from __future__ import annotations

import json
from pathlib import Path
import sys
import re

from .chapterizer import simple_chapterize, write_chapter_json
from .pdf import extract_pdf_text


def heuristic_chapterize_pages(book_id: str, pages: list[str]) -> list[str]:
    """Split pages into chapter-sized blocks using simple heading heuristics.

    Heuristics:
    - A line in ALL CAPS (>= 3 chars) or starting with 'Chapter'
      denotes a new chapter.
    - Page breaks always allowed boundaries.
    - Minimum chapter length aggregation to avoid tiny single-page
      chapters (< 400 chars unless heading).
    """
    chapters: list[str] = []
    buf: list[str] = []
    acc_len = 0
    heading_re = re.compile(
        r"^(chapter(\s+\d+|\s+[xivlcdm]+)?)|[A-Z0-9 '\-:,]{3,}$",
        re.IGNORECASE,
    )
    for page in pages:
        lines = page.splitlines()
        is_heading_page = False
        for ln in lines[:5]:  # inspect first few lines
            if heading_re.match(ln.strip()) and len(ln.strip()) < 120:
                is_heading_page = True
                break
        if is_heading_page and acc_len >= 400 and buf:
            chapters.append("\n\n".join(buf))
            buf = []
            acc_len = 0
        buf.append(page.strip())
        acc_len += len(page)
    if buf:
        chapters.append("\n\n".join(buf))
    return chapters


def ingest_pdf(book_id: str, pdf_path: Path, out_root: Path) -> None:
    """Ingest PDF using layered extractors with fallback and heuristics."""
    result = extract_pdf_text(pdf_path)
    raw_pages = result.pages or [result.text]
    page_based = heuristic_chapterize_pages(book_id, raw_pages)
    # Fallback to size-based simple splitter if heuristic produced
    # one giant chunk
    if len(page_based) <= 1:
        combined = "\n\n".join(raw_pages)
        chapters_objs = simple_chapterize(book_id, combined)
    else:
        chapters_objs = []
        for i, chunk in enumerate(page_based):
            from .chapterizer import sha256_text, Chapter, default_title

            chapters_objs.append(
                Chapter(
                    book_id=book_id,
                    chapter_id=f"{i:05d}",
                    index=i,
                    title=default_title(i),
                    text=chunk,
                    text_sha256=sha256_text(chunk),
                )
            )
    out_dir = out_root / "clean" / book_id
    for ch in chapters_objs:
        p = write_chapter_json(ch, out_dir)
        print(
            json.dumps(
                {
                    "chapter_id": ch.chapter_id,
                    "path": str(p),
                    "backend": result.backend.value,
                    "warnings": result.warnings,
                }
            )
        )


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "Usage: ingest-pdf <book_id> <pdf_or_txt_path> [out_root=data]",
            file=sys.stderr,
        )
        return 1
    book_id = argv[1]
    pdf_path = Path(argv[2])
    out_root = Path(argv[3]) if len(argv) > 3 else Path("data")
    ingest_pdf(book_id, pdf_path, out_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
