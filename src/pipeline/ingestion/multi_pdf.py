"""Multi-PDF ingestion helper.

Turns a set of PDF files (already logically split by chapter) into
per‑chapter JSON artifacts (reusing existing chapter JSON schema) plus
an aggregated chapters.jsonl for downstream bulk processes.

Usage (CLI):
  python -m pipeline.ingestion.multi_pdf <book_id> <pdf_dir_or_glob> <out_root>

Assumptions:
  * Each PDF corresponds to exactly one chapter.
  * Chapter ordering is lexicographic by filename unless an explicit
    mapping file is provided (future extension).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .chapterizer import Chapter, sha256_text, write_chapter_json
from .pdf import extract_pdf_text


@dataclass
class IngestedChapter:
    """Lightweight record for an ingested single-PDF chapter."""

    id: str
    path: Path
    json_path: Path
    index: int
    title: str
    text_sha256: str


def _slug_from_filename(p: Path) -> str:
    base = p.stem.lower().replace(" ", "_")
    # Short hash to avoid collisions if duplicate stems
    h = hashlib.sha256(p.name.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{h}"[:32]


def ingest_pdf_files(
    book_id: str,
    pdf_paths: Iterable[Path],
    out_root: Path = Path("data/clean"),
    include_text_files: bool = True,
) -> List[IngestedChapter]:
    """Ingest multiple single-chapter PDF files for a book.

    Each PDF is treated as a single chapter whose numeric id is the
    enumeration order (sorted by path). Creates per-chapter JSON (and
    optional plain text) plus an aggregated ``chapters.jsonl`` mapping.

    Args:
        book_id: Stable book identifier.
        pdf_paths: Iterable of paths (glob results or directory list).
        out_root: Root directory under which ``<book_id>`` is created.
        include_text_files: Also write ``<chapter_id>.txt`` alongside JSON.

    Returns:
        List of ingested chapter metadata objects.
    """
    logger = logging.getLogger(__name__)
    pdf_list = sorted([p for p in map(Path, pdf_paths) if p.exists()])
    if not pdf_list:
        raise ValueError("No PDF files found for ingestion")
    chapter_dir = out_root / book_id
    chapter_dir.mkdir(parents=True, exist_ok=True)

    ingested: List[IngestedChapter] = []
    for idx, pdf in enumerate(pdf_list):
        res = extract_pdf_text(pdf)
        # Use extracted text (can be empty if backend fails, allowed)
        text = res.text
        if not text.strip():  # fallback minimal placeholder
            text = ""
        # Basic metadata counts (lightweight)
        word_count = len(re.findall(r"\b\w+\b", text)) if text else 0
        para_count = (
            len([p for p in text.split("\n\n") if p.strip()]) if text else 0
        )
        sent_count = (
            len(
                [
                    s
                    for s in re.split(r"(?<=[.!?])\s+", text.strip())
                    if s
                ]
            )
            if text
            else 0
        )
        chapter_id = f"{idx:05d}"  # stable numeric ID
        # Derive a human-ish title from filename
        title = pdf.stem
        # Build Chapter dataclass for reuse of existing JSON writer
        ch = Chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            index=idx,
            title=title,
            text=text,
            text_sha256=sha256_text(text),
        )
        json_path = write_chapter_json(ch, chapter_dir)
        if include_text_files:
            (chapter_dir / f"{chapter_id}.txt").write_text(
                text, encoding="utf-8"
            )
        ingested.append(
            IngestedChapter(
                id=f"{book_id}-{chapter_id}",
                path=pdf,
                json_path=json_path,
                index=idx,
                title=title,
                text_sha256=ch.text_sha256,
            )
        )

    # Write aggregated chapters.jsonl
    jsonl_path = chapter_dir / "chapters.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for ch in ingested:
            record = {
                "id": ch.id,
                "book_id": book_id,
                "chapter_id": f"{ch.index:05d}",
                "index": ch.index,
                "title": ch.title,
                "text_sha256": ch.text_sha256,
                # Point back to per‑chapter JSON (contains text)
                "json_path": str(ch.json_path),
                "source_pdf": str(ch.path),
                # Minimal metadata (word/sentence/paragraph counts best-effort)
                "meta": {
                    "source": "multi_pdf",
                    "word_count": word_count,
                    "paragraph_count": para_count,
                    "sentence_count": sent_count,
                },
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(
        "Ingested %d PDFs for book=%s into %s",
        len(ingested),
        book_id,
        chapter_dir,
    )
    return ingested


def _expand_glob(arg: str) -> List[Path]:
    """Return PDF paths from a directory or glob pattern."""
    p = Path(arg)
    if p.is_dir():
        return list(p.glob("*.pdf"))
    # Shell might not expand globs when invoked programmatically.
    return list(p.parent.glob(p.name))


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for multi-PDF ingestion.

    Returns exit status code (0 on success). Emits progress via logging.
    """
    logger = logging.getLogger(__name__)
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        logger.error(
            "Usage: python -m pipeline.ingestion.multi_pdf "
            "<book_id> <pdf_dir_or_glob> [out_root]"
        )
        return 1
    book_id = argv[0]
    glob_arg = argv[1]
    out_root = Path(argv[2]) if len(argv) > 2 else Path("data/clean")
    pdfs = _expand_glob(glob_arg)
    if not pdfs:
        logger.error("No PDFs matched input path pattern=%s", glob_arg)
        return 2
    ingest_pdf_files(book_id, pdfs, out_root=out_root)
    logger.info(
        "Completed ingest of %d PDFs into %s", len(pdfs), out_root / book_id
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
