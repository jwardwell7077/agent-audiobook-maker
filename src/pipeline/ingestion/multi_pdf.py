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

import json
import logging
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from .chapterizer import Chapter, sha256_text, write_chapter_json
from .pdf import pdf_to_text


@dataclass
class IngestedChapter:
    """Lightweight record for an ingested single-PDF chapter."""

    id: str
    path: Path
    json_path: Path
    index: int
    title: str
    text_sha256: str


# Removed unused _slug_from_filename helper (kept history via VCS)


@runtime_checkable
class _HasText(Protocol):
    text: str


def extract_pdf_text(path: Path) -> _HasText:
    """Legacy-compatible wrapper returning an object with .text attribute.

    Tests monkeypatch multi_pdf.extract_pdf_text; preserve that surface by
    returning a simple object with the extracted text.
    """

    class DummyResult:
        def __init__(self, text: str) -> None:
            self.text = text

    return DummyResult(pdf_to_text(path))


def ingest_pdf_files(
    book_id: str,
    pdf_paths: Iterable[Path],
    out_root: Path = Path("data/clean"),
    include_text_files: bool = True,
) -> list[IngestedChapter]:
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

    ingested: list[IngestedChapter] = []
    for idx, pdf in enumerate(pdf_list):
        text = pdf_to_text(pdf)
        if not text.strip():  # fallback minimal placeholder
            text = ""
        # Basic metadata counts computed later when writing JSONL
        chapter_id = f"{idx:05d}"  # stable numeric ID
        # Derive a human-ish title from filename
        title = pdf.stem
        # Build Chapter dataclass for reuse of existing JSON writer
        chapter_obj = Chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            index=idx,
            title=title,
            text=text,
            text_sha256=sha256_text(text),
        )
        json_path = write_chapter_json(chapter_obj, chapter_dir)
        if include_text_files:
            (chapter_dir / f"{chapter_id}.txt").write_text(text, encoding="utf-8")
        ingested.append(
            IngestedChapter(
                id=f"{book_id}-{chapter_id}",
                path=pdf,
                json_path=json_path,
                index=idx,
                title=title,
                text_sha256=chapter_obj.text_sha256,
            )
        )

    # Write aggregated chapters.jsonl
    jsonl_path = chapter_dir / "chapters.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for ing_ch in ingested:
            # Recompute lightweight counts per record (avoid capturing vars)
            txt = (
                (chapter_dir / f"{ing_ch.index:05d}.txt").read_text(encoding="utf-8")
                if (chapter_dir / f"{ing_ch.index:05d}.txt").exists()
                else ""
            )
            wc = len(re.findall(r"\b\w+\b", txt)) if txt else 0
            pc = len([p for p in txt.split("\n\n") if p.strip()]) if txt else 0
            sc = len([s for s in re.split(r"(?<=[.!?])\s+", txt.strip()) if s]) if txt else 0
            record = {
                "id": ing_ch.id,
                "book_id": book_id,
                "chapter_id": f"{ing_ch.index:05d}",
                "index": ing_ch.index,
                "title": ing_ch.title,
                "text_sha256": ing_ch.text_sha256,
                "json_path": str(ing_ch.json_path),
                "source_pdf": str(ing_ch.path),
                "meta": {
                    "source": "multi_pdf",
                    "word_count": wc,
                    "paragraph_count": pc,
                    "sentence_count": sc,
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


def _expand_glob(arg: str) -> list[Path]:
    """Return PDF paths from a directory or glob pattern."""
    p = Path(arg)
    if p.is_dir():
        return list(p.glob("*.pdf"))
    # Shell might not expand globs when invoked programmatically.
    return list(p.parent.glob(p.name))


ARGC_MIN = 2


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for multi-PDF ingestion.

    Returns exit status code (0 on success). Emits progress via logging.
    """
    logger = logging.getLogger(__name__)
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < ARGC_MIN:
        usage = "Usage: python -m pipeline.ingestion.multi_pdf <book_id> <glob> [out]"
        logger.error(usage)
        # Also emit to stderr for CLI tests capturing output
        print(usage, file=sys.stderr)
        return 1
    book_id = argv[0]
    glob_arg = argv[1]
    out_root = Path(argv[2]) if len(argv) > ARGC_MIN else Path("data/clean")
    pdfs = _expand_glob(glob_arg)
    if not pdfs:
        logger.error("No PDFs matched input path pattern=%s", glob_arg)
        return 2
    ingested = ingest_pdf_files(book_id, pdfs, out_root=out_root)
    # Explicit stdout line for tests expecting this phrasing.
    # Mirror info via logger only (removed print for Ruff compliance)
    logger.info("Ingested %s PDFs for book %s", len(ingested), book_id)
    # Also print a concise summary to stdout for tests
    print(f"Ingested {len(ingested)} PDFs", file=sys.stdout)
    completion = f"Completed ingest of {len(pdfs)} PDFs into {out_root / book_id}"
    logger.info(completion)
    # Removed print duplicate (logger already emitted completion)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
