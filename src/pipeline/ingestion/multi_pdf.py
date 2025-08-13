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

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import hashlib
import json
import sys

from .pdf import extract_pdf_text
from .chapterizer import write_chapter_json, sha256_text, Chapter


@dataclass
class IngestedChapter:
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
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return ingested


def _expand_glob(arg: str) -> List[Path]:
    p = Path(arg)
    if p.is_dir():
        return list(p.glob("*.pdf"))
    # shell might not expand globs when invoked programmatically
    return list(p.parent.glob(p.name))


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print(
            "Usage: python -m pipeline.ingestion.multi_pdf "
            "<book_id> <pdf_dir_or_glob> [out_root]",
            file=sys.stderr,
        )
        return 1
    book_id = argv[0]
    glob_arg = argv[1]
    out_root = Path(argv[2]) if len(argv) > 2 else Path("data/clean")
    pdfs = _expand_glob(glob_arg)
    if not pdfs:
        print("No PDFs matched input path", file=sys.stderr)
        return 2
    ingest_pdf_files(book_id, pdfs, out_root=out_root)
    print(
        (
            "Ingested {n} PDFs into {dest} "
            "(per-chapter JSON + chapters.jsonl)"
        ).format(n=len(pdfs), dest=out_root / book_id)
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
