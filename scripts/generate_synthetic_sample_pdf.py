"""Generate a deterministic synthetic sample PDF with intro + TOC + chapters.

Purpose:
    Provide a public-domain friendly placeholder book (SAMPLE_BOOK) for
    ingestion, chapterization, and regression tests without including any
    proprietary text. Content is intentionally generic but structured to
    exercise the structured TOC parser and downstream pipeline.

Features:
    - Intro section preceding the Table of Contents.
    - Table of Contents listing N chapters (default 10).
    - Chapter headings in the form: "Chapter X: Title X".
    - Deterministic pseudo-random filler paragraphs for stable hashes.
    - Uses PyMuPDF (fitz) which is already a runtime dependency.

Usage (from repo root):
    python scripts/generate_synthetic_sample_pdf.py \
        --book-id SAMPLE_BOOK \
        --chapters 10 \
        --out data/books/SAMPLE_BOOK/source_pdfs/synthetic_sample.pdf

After generation you can ingest with:
    curl -X POST -F book_id=SAMPLE_BOOK -F pdf_name=synthetic_sample.pdf \
        http://localhost:8000/ingest

"""

from __future__ import annotations

import argparse
import datetime as _dt
import random
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:  # local import; will raise if dependency missing
    import fitz  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("PyMuPDF (fitz) is required. Ensure 'pymupdf' is installed.") from e


LOREM_BASE = [
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet",
    "consectetur",
    "adipiscing",
    "elit",
    "sed",
    "do",
    "eiusmod",
    "tempor",
    "incididunt",
    "ut",
    "labore",
    "et",
    "dolore",
    "magna",
    "aliqua",
]


def _make_paragraph(rng: random.Random, min_words: int = 40, max_words: int = 70) -> str:  # noqa: D401
    n = rng.randint(min_words, max_words)
    words = [rng.choice(LOREM_BASE) for _ in range(n)]
    # Capitalize first word and end with period.
    words[0] = words[0].capitalize()
    para = " ".join(words)
    if not para.endswith("."):
        para += "."
    return textwrap.fill(para, width=78)


def build_book(chapters: int, seed: int) -> dict[str, Any]:
    """Build deterministic synthetic book structure.

    Returns a mapping with intro text, toc entry list, and chapter bodies.
    """
    rng = random.Random(seed)  # noqa: S311 - deterministic non-crypto usage
    intro_paras = [_make_paragraph(rng) for _ in range(2)]
    intro = "\n\n".join(intro_paras)
    toc_entries = [f"Chapter {i}: Title {i}" for i in range(1, chapters + 1)]
    chapter_bodies = []
    for i in range(1, chapters + 1):
        body_paras = [_make_paragraph(rng) for _ in range(rng.randint(2, 4))]
        body = f"Chapter {i}: Title {i}\n" + "\n\n".join(body_paras)
        chapter_bodies.append(body)
    return {"intro": intro, "toc": toc_entries, "chapters": chapter_bodies}


def write_pdf(book: dict[str, Any], out_path: Path) -> None:
    """Write synthetic book structure to a PDF file at ``out_path``."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    # Intro + TOC page(s)
    intro_text = [
        "Synthetic Sample Book",
        f"Generated: {_dt.datetime.utcnow().isoformat()}Z",
        "",
        book["intro"],
        "",
        "Table of Contents",
        *book["toc"],
        "",
    ]
    _add_wrapped_page(doc, "\n".join(intro_text))
    # Chapters
    for ch_body in book["chapters"]:
        _add_wrapped_page(doc, ch_body)
    doc.save(out_path)
    doc.close()


if TYPE_CHECKING:  # pragma: no cover
    pass


def _add_wrapped_page(doc: Any, raw: str) -> None:  # noqa: ANN401
    """Add a page with wrapped text blocks to the provided document.

    ``doc`` is a PyMuPDF Document; typed as ``Any`` to avoid import-time
    dependency for static analysis in minimal environments.

    Args:
        doc: Open PyMuPDF document instance.
        raw: Raw multi-line text content for the page.
    """
    page = doc.new_page()
    # Simple top-left text writer; fitz will wrap lines we provide.
    cursor_y = 36
    for block in raw.splitlines():
        # Manual wrap at ~90 chars for deterministic layout
        for wrapped in textwrap.wrap(block, width=90) or [""]:
            page.insert_text((36, cursor_y), wrapped)
            cursor_y += 14
        cursor_y += 6  # paragraph spacing


def main() -> None:
    """CLI entrypoint for synthetic sample PDF generation."""
    ap = argparse.ArgumentParser(description="Generate synthetic sample PDF")
    ap.add_argument(
        "--book-id",
        default="SAMPLE_BOOK",
        help="Book id directory under data/books/",
    )
    ap.add_argument(
        "--chapters",
        type=int,
        default=10,
        help="Number of chapters (default 10)",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Deterministic RNG seed for stable content",
    )
    ap.add_argument(
        "--out",
        default="data/books/SAMPLE_BOOK/source_pdfs/synthetic_sample.pdf",
        help="Output PDF path",
    )
    args = ap.parse_args()
    book = build_book(args.chapters, args.seed)
    out_path = Path(args.out)
    write_pdf(book, out_path)
    import sys as _sys

    _sys.stdout.write(f"Wrote synthetic PDF -> {out_path} (chapters={args.chapters})\n")


if __name__ == "__main__":  # pragma: no cover
    main()
