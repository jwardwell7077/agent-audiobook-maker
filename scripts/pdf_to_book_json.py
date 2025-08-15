#!/usr/bin/env python3
"""
Utility: pdf_to_book_json.py

Converts a PDF into plain text, then parses a lightweight book structure JSON:
{
  "source_pdf": "...",
  "extracted_txt": "...",
  "intro": "...",
  "toc": [ {"number": 1, "title": "..."}, ...],
  "chapters": [ {"number": 1, "title": "...", "text": "..."}, ...]
}

Usage:
    python scripts/pdf_to_book_json.py /path/to/book.pdf
    # (optional overrides)
    python scripts/pdf_to_book_json.py /path/to/book.pdf \
        --txt /tmp/book.txt --json /tmp/book.json

Notes:
- Detects a 'Table of Contents' block and chapter lines like 'Chapter N: Title'.
- If no TOC header is found, text before first chapter header becomes intro.
- Relocated from a transient temp/ area into scripts/; logic unchanged.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

TOC_HEADER_RE = re.compile(
    r'^\s*Table of Contents\b.*$', re.IGNORECASE | re.MULTILINE
)
TOC_LINE_RE = re.compile(
    r'^\s*(?:[•\-*]\s*)?Chapter\s+(\d{1,4})\s*:\s*(.+?)\s*$', re.IGNORECASE
)
CH_HDR_RE = re.compile(
    r'^\s*Chapter\s+(\d{1,4})\s*:\s*(.+?)\s*$', re.IGNORECASE | re.MULTILINE
)

 
def extract_pdf_to_text(pdf_path: Path) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    return "\n\n".join(pages)

 
def parse_text_to_structure(full_text: str) -> dict:
    text = full_text.replace("\r\n", "\n").replace("\r", "\n")
    toc = []
    intro = ""
    toc_region = None

    m_toc_hdr = TOC_HEADER_RE.search(text)
    if m_toc_hdr:
        start_hdr, end_hdr = m_toc_hdr.span()
        substr = text[end_hdr:]
        offset = end_hdr
        nonmatch_streak = 0
        last_match_end = end_hdr
        saw_any = False
        for line in substr.splitlines(keepends=True):
            mo = TOC_LINE_RE.match(line)
            if mo:
                nonmatch_streak = 0
                saw_any = True
                try:
                    num = int(mo.group(1))
                except ValueError:
                    num = -1
                title = mo.group(2).strip()
                if 1 <= num <= 3000:
                    toc.append({"number": num, "title": title})
                last_match_end = offset + len(line)
            else:
                nonmatch_streak += 1
                if saw_any and nonmatch_streak >= 3:
                    break
            offset += len(line)
        toc_region = (start_hdr, last_match_end if saw_any else end_hdr)
        intro = text[:start_hdr].strip()

    ch_matches = []
    for mo in CH_HDR_RE.finditer(text):
        s, e = mo.span()
        if toc_region and toc_region[0] <= s < toc_region[1]:
            continue
        try:
            num = int(mo.group(1))
        except ValueError:
            continue
        if not (1 <= num <= 3000):
            continue
        title = mo.group(2).strip()
        ch_matches.append((s, e, num, title))

    ch_matches.sort(key=lambda t: t[0])
    if not m_toc_hdr and ch_matches and ch_matches[0][0] > 0:
        intro = text[:ch_matches[0][0]].strip()

    chapters = []
    for i, (s, e, num, title) in enumerate(ch_matches):
        next_start = (
            ch_matches[i + 1][0] if i + 1 < len(ch_matches) else len(text)
        )
        body = text[e:next_start].strip()
        chapters.append({
            "number": num,
            "title": title,
            "text": body
        })

    toc_sorted = sorted(toc, key=lambda x: x["number"]) if toc else []
    return {"intro": intro, "toc": toc_sorted, "chapters": chapters}

 
def main():
    ap = argparse.ArgumentParser(
        description="Render PDF; parse to JSON (intro, toc, chapters)."
    )
    ap.add_argument("pdf", type=Path, help="Path to input PDF")
    ap.add_argument(
        "--txt",
        type=Path,
        help="Where to write extracted text (default: alongside PDF)",
    )
    ap.add_argument(
        "--json",
        type=Path,
        help="Where to write JSON (default: alongside PDF)",
    )
    args = ap.parse_args()
    pdf_path = args.pdf
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    txt_out = args.txt or pdf_path.with_suffix(".txt")
    json_out = args.json or pdf_path.with_suffix(".json")
    full_text = extract_pdf_to_text(pdf_path)
    txt_out.write_text(full_text, encoding="utf-8")
    structure = parse_text_to_structure(full_text)
    payload = {
        "source_pdf": str(pdf_path.resolve()),
        "extracted_txt": str(txt_out.resolve()),
        **structure,
    }
    json_out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"TXT written:  {txt_out}")
    print(f"JSON written: {json_out}")

 
if __name__ == "__main__":
    main()
