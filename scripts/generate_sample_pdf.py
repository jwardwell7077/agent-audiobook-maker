#!/usr/bin/env python3
"""Generate a deterministic synthetic demo PDF for ingestion tests.

Creates a SAMPLE_BOOK PDF with:
  - An intro section (prior to the TOC header)
  - A 'Table of Contents' header followed by canonical chapter lines
  - 10 chapters each with a heading 'Chapter N: Title N' and fixed body text

Why this exists:
  The ingestion pipeline relies on structured TOC + chapter headings.
  We need a public, license‑safe sample artifact to exercise parsing and
  (later) stable hash regression tests. This generator produces
  deterministic content so downstream hashes remain stable across runs.

Usage (default output path):
  python scripts/generate_sample_pdf.py

Optional flags:
  --book-id BOOK_ID        (default: SAMPLE_BOOK)
  --chapters N             (default: 10)
  --output PATH.pdf        (override output path)
  --overwrite              (allow replacing an existing file)

Dependencies: pymupdf (installed as 'pymupdf').
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import datetime as _dt

try:  # Lazy import so help text still works without dependency
    import fitz  # type: ignore
except Exception as e:  # noqa: BLE001
    print("ERROR: pymupdf (fitz) not installed:", e, file=sys.stderr)
    sys.exit(2)


DEFAULT_BOOK_ID = "SAMPLE_BOOK"


def build_intro(book_id: str, chapter_count: int) -> str:
    return (
        f"This is a synthetic sample book (book_id={book_id}).\n\n"
        "It is generated purely for demonstrating the structured TOC "
        "ingestion pipeline. The content is deterministic so that "
        "hashes computed over chapter bodies will remain stable across "
        "runs (barring code changes).\n\n"  # noqa: E501
        f"Generated on: {_dt.date.today().isoformat()}\n"
        f"Chapter count (excluding Intro): {chapter_count}\n"
        "--- End Intro ---\n"
    )


def build_toc(chapter_count: int) -> str:
    lines = ["Table of Contents"]
    for i in range(1, chapter_count + 1):
        lines.append(f"Chapter {i}: Title {i}")
    return "\n".join(lines)


def build_chapter_body(i: int) -> str:
    base_para = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non "
        "risus. Suspendisse lectus tortor, dignissim sit amet, adipiscing "
        "nec, ultricies sed, dolor. Cras elementum ultrices diam. Donec "
        "faucibus, nisl id ultrices posuere, nunc risus tempus sapien, at "
        "luctus lorem justo sit amet massa. "
    )
    # Make each chapter body unique yet deterministic by repeating i times.
    repeated = " ".join([base_para.strip()] * (1 + (i % 3)))
    return (
        f"Chapter {i}: Title {i}\n"
        f"{repeated}\n\n(This concludes chapter {i}.)"
    )


def generate_pdf(path: Path, book_id: str, chapter_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    intro_page = doc.new_page()
    intro_text = build_intro(book_id, chapter_count)
    intro_page.insert_text((72, 72), intro_text, fontsize=12)

    toc_page = doc.new_page()
    toc_text = build_toc(chapter_count)
    toc_page.insert_text((72, 72), toc_text, fontsize=12)

    for i in range(1, chapter_count + 1):
        pg = doc.new_page()
        body = build_chapter_body(i)
        pg.insert_text((72, 72), body, fontsize=12)

    doc.save(str(path))
    doc.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate synthetic sample book PDF"
    )
    p.add_argument("--book-id", default=DEFAULT_BOOK_ID)
    p.add_argument("--chapters", type=int, default=10)
    p.add_argument(
        "--output",
        type=Path,
        help="Override output PDF path (default derived from book id)",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing file",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv or sys.argv[1:])
    out_path = ns.output
    if not out_path:
        out_path = (
            Path("data/books") / ns.book_id / "source_pdfs" / "sample.pdf"
        )
    if out_path.exists() and not ns.overwrite:
        print(
            f"Refusing to overwrite existing file: {out_path} (use --overwrite)",
            file=sys.stderr,
        )
        return 1
    generate_pdf(out_path, ns.book_id, ns.chapters)
    print(
        f"Generated synthetic PDF: {out_path} (chapters={ns.chapters}, book_id={ns.book_id})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
