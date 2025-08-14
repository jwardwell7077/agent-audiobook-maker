"""Shared ingestion core utilities (structured TOC only).

This module now enforces a single parsing strategy: structured TOC.
If a structured TOC can't be parsed we return with a warning and no
chapters so the caller can decide how to surface the failure.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Sequence
import logging
import time
import json

from .pdf import extract_pdf_text, PDFExtractionResult
from .parsers.structured_toc import parse_structured_toc
from .chapterizer import Chapter, write_chapter_json, sha256_text

logger = logging.getLogger(__name__)


def _basic_text_meta(text_block: str) -> Dict[str, Any]:
    import re as _re
    tb = text_block or ""
    sentences = [s for s in _re.split(r"(?<=[.!?])\s+", tb.strip()) if s]
    paragraphs = [p for p in tb.split("\n\n") if p.strip()]
    words = _re.findall(r"\b\w+\b", tb)
    return {
        "word_count": len(words),
        "char_count": len(tb),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
    }


def extract_and_chapterize(
    book_id: str,
    pdf_path: Path,
    next_index_start: int,
    skip_if: Optional[Sequence[str]] = None,
    chunk_page_size: int | None = None,  # retained for signature stability
) -> Tuple[
    List[dict],
    int,
    PDFExtractionResult,
    List[str],
    int,
    Optional[float],
    Optional[float],
    bool,
    Optional[int],
    Optional[int],
    Optional[str],
    Optional[str],
]:
    """Extract PDF text and chapterize using ONLY structured TOC.

    Returns tuple matching previous public contract consumed by API.
    Fallback strategies have been removed. If parse fails, returns empty
    records with warning 'structured_toc_parse_failed'.
    """
    # skip_if now expected to contain chapter titles (and/or record ids) that
    # should not be re‑emitted on re‑ingest. This avoids duplicating chapters
    # when reprocessing the same PDF without purging.
    skip_set = set(skip_if or [])
    warnings: List[str] = []
    # 1. Extract
    t_ext = time.perf_counter()
    result = extract_pdf_text(pdf_path)
    extraction_ms = (time.perf_counter() - t_ext) * 1000.0
    pages = result.pages or [result.text]
    text = result.text or "\n".join(pages)
    warnings.extend(result.warnings)

    # 2. Parse structured TOC
    t_struct = time.perf_counter()
    try:
        structured = parse_structured_toc(text)
    except Exception as e:  # pragma: no cover
        logger.exception("structured_toc_exception pdf=%s", pdf_path.name)
        structured = None
        warnings.append(f"structured_toc_exception: {e}")
    chapterization_ms = (time.perf_counter() - t_struct) * 1000.0
    parse_mode: str | None = "structured_toc"

    if not structured:
        warnings.append("structured_toc_parse_failed")
        logger.warning("structured_toc_parse_failed pdf=%s", pdf_path.name)
        return (
            [],
            next_index_start,
            result,
            warnings,
            len(pages),
            extraction_ms,
            chapterization_ms,
            False,
            None,
            None,
            parse_mode,
            None,
        )

    chapters_local: List[Chapter] = []
    intro_text = structured.get("intro") or ""
    if intro_text.strip():
        chapters_local.append(
            Chapter(
                book_id=book_id,
                chapter_id="INTRO",
                index=0,
                title="Intro",
                text=intro_text.strip(),
                text_sha256=sha256_text(intro_text.strip()),
            )
        )
    for ch in structured.get("chapters", []):
        body = ch["text"]
        title = f"Chapter {ch['number']}: {ch['title']}"
        chapters_local.append(
            Chapter(
                book_id=book_id,
                chapter_id=f"{ch['number']:05d}",
                index=ch["number"],
                title=title,
                text=body,
                text_sha256=sha256_text(body),
            )
        )
    logger.info(
        "structured_toc_parse_success pdf=%s chapters=%s",
        pdf_path.name,
        len(chapters_local),
    )

    # 3. Persist chapters & volume JSON
    out_dir = Path("data/clean") / book_id
    out_dir.mkdir(parents=True, exist_ok=True)
    records: List[dict] = []
    next_index = next_index_start

    volume: Dict[str, Any] = {
        "schema_version": "1.0",
        "book_id": book_id,
        "pdf_name": pdf_path.name,
        "pdf_stem": pdf_path.stem,
        "parse_mode": parse_mode,
        "extraction_ms": extraction_ms,
        "chapterization_ms": chapterization_ms,
        "page_count": len(pages),
        "chapter_count": len(chapters_local),
        "toc_count": len(structured.get("toc", [])),
        "heading_count": len(structured.get("chapters", [])),
        "intro_present": bool(intro_text.strip()),
        "toc": structured.get("toc", []),
        "chapters": [],
        "warnings": warnings,
    }

    # Consistency checks: mismatches between toc entries, headings, and emitted
    # chapter objects are often due to extraction glitches (duplicate lines or
    # lost spacing). Emit lightweight warnings to aid debugging.
    toc_numbers = {e["number"] for e in structured.get("toc", [])}
    heading_numbers = {c["number"] for c in structured.get("chapters", [])}
    if toc_numbers and heading_numbers:
        missing_from_headings = sorted(toc_numbers - heading_numbers)
        missing_from_toc = sorted(heading_numbers - toc_numbers)
        if missing_from_headings:
            warnings.append(
                "toc_numbers_without_headings:" + ",".join(
                    map(str, missing_from_headings)
                )
            )
        if missing_from_toc:
            warnings.append(
                "headings_without_toc_numbers:" + ",".join(
                    map(str, missing_from_toc)
                )
            )
        if len(toc_numbers) != volume["toc_count"]:
            warnings.append(
                f"toc_dedup_removed={volume['toc_count'] - len(toc_numbers)}"
            )

    for ch in chapters_local:
        new_idx = next_index
        next_index += 1
        # Re-index sequentially (global book index) regardless of parsed number
        new_ch = Chapter(
            book_id=ch.book_id,
            chapter_id=f"{new_idx:05d}",
            index=new_idx,
            title=ch.title,
            text=ch.text,
            text_sha256=ch.text_sha256,
        )
        record_id = f"{book_id}-{new_ch.chapter_id}"
        if (record_id in skip_set) or (new_ch.title in skip_set):
            logger.debug(
                "skip_existing_chapter id=%s title=%s", record_id, new_ch.title
            )
            continue
        p = write_chapter_json(new_ch, out_dir)
        meta = _basic_text_meta(new_ch.text)
        chapter_number = None
        parts = new_ch.title.split()
        if (
            len(parts) >= 2
            and parts[0].lower() == "chapter"
            and parts[1].rstrip(":").isdigit()
        ):
            try:
                chapter_number = int(parts[1].rstrip(":"))
            except ValueError:  # pragma: no cover
                chapter_number = None
        vol_entry = {
            "chapter_id": new_ch.chapter_id,
            "index": new_ch.index,
            "title": new_ch.title,
            "number": chapter_number,
            "start_page": None,
            "end_page": None,
            "page_count": None,
            "word_count": meta["word_count"],
            "char_count": meta["char_count"],
            "sentence_count": meta["sentence_count"],
            "paragraph_count": meta["paragraph_count"],
            "source": "structured_toc",
            "json_path": str(p),
            "text_sha256": new_ch.text_sha256,
        }
        volume["chapters"].append(vol_entry)
        records.append(
            {
                "id": record_id,
                "book_id": book_id,
                "index": new_ch.index,
                "title": new_ch.title,
                "text_sha256": new_ch.text_sha256,
                "json_path": str(p),
                "chapter_id": new_ch.chapter_id,
                "source_pdf_name": pdf_path.name,
                "meta": meta
                | {
                    "source": "structured_toc",
                    "chapter_number": chapter_number,
                },
            }
        )

    volume_json_path: str | None = None
    try:
        vol_path = out_dir / f"{pdf_path.stem}_volume.json"
        vol_path.write_text(
            json.dumps(volume, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        volume_json_path = str(vol_path)
    except Exception:  # pragma: no cover
        logger.exception("volume_json_write_error pdf=%s", pdf_path.name)

    return (
        records,
        next_index,
        result,
        warnings,
        len(pages),
        extraction_ms,
        chapterization_ms,
        False,  # chunked
        None,  # chunk_size_used
        None,  # chunk_count
        parse_mode,
        volume_json_path,
    )


def enumerate_pdfs(book_id: str) -> List[Path]:
    book_dir = Path("data/books") / book_id
    source_dir = book_dir / "source_pdfs"
    pdfs: List[Path] = []
    if book_dir.exists():
        pdfs.extend(sorted(book_dir.glob("*.pdf")))
    if source_dir.exists():
        pdfs.extend(sorted(source_dir.glob("*.pdf")))
    return pdfs
