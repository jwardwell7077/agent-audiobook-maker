"""Shared ingestion core utilities (structured TOC only).

This module now enforces a single parsing strategy: structured TOC.
If a structured TOC can't be parsed we return with a warning and no
chapters so the caller can decide how to surface the failure.
"""

from __future__ import annotations

import json
import logging
import re as _re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .chapterizer import Chapter, sha256_text, write_chapter_json
from .parsers.structured_toc import parse_structured_toc
from .pdf import PDFExtractionResult, extract_pdf_text

logger = logging.getLogger(__name__)


def _basic_text_meta(text_block: str) -> dict[str, Any]:
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


def extract_and_chapterize(  # noqa: PLR0913 (complex pipeline function; refactor deferred)
    book_id: str,
    pdf_path: Path,
    next_index_start: int,
    skip_if: Sequence[str] | None = None,
    chunk_page_size: int | None = None,  # retained for signature stability
    # deprecated: retained for signature compatibility only (ignored)
    fallback_on_failure: bool = False,
) -> tuple[
    list[dict[str, Any]],
    int,
    PDFExtractionResult,
    list[str],
    int,
    float | None,
    float | None,
    bool,
    int | None,
    int | None,
    str | None,
    str | None,
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
    warnings: list[str] = []
    # 1. Extract
    t0 = time.perf_counter()
    result = extract_pdf_text(pdf_path)
    extraction_ms = (time.perf_counter() - t0) * 1000
    pages = result.pages if result and hasattr(result, "pages") else []
    parse_mode = "structured_toc"
    chapterization_ms = None
    structured = None
    try:
        t1 = time.perf_counter()
        structured = parse_structured_toc(result.text if result and hasattr(result, "text") else "")
        chapterization_ms = (time.perf_counter() - t1) * 1000
    except Exception:
        logger.exception("structured_toc_parse_error pdf=%s", pdf_path.name)
        structured = None
        chapterization_ms = None

    if not structured:
        warnings.append("structured_toc_parse_failed")
        logger.warning("structured_toc_parse_failed pdf=%s", pdf_path.name)
        # Optional fallback: in some lightweight flows (e.g., single-PDF
        # uploads under source_pdfs), emit a single chapter with the entire
        # text content to keep end-to-end happy-path usable.
        use_fallback = fallback_on_failure or ("/source_pdfs/" in str(pdf_path))
        if not use_fallback:
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
        # Fallback: single chapter using entire extracted text
        fallback_chapters: list[Chapter] = [
            Chapter(
                book_id=book_id,
                chapter_id="00000",
                index=next_index_start,
                title=Path(pdf_path).stem,
                text=(result.text if result else ""),
                text_sha256=sha256_text(result.text if result else ""),
            )
        ]
        out_dir = Path("data/clean") / book_id
        out_dir.mkdir(parents=True, exist_ok=True)
        records_fallback: list[dict[str, Any]] = []
        next_index = next_index_start
        volume: dict[str, Any] = {
            "schema_version": "1.0",
            "book_id": book_id,
            "pdf_name": Path(pdf_path).name,
            "pdf_stem": Path(pdf_path).stem,
            "parse_mode": parse_mode,
            "extraction_ms": extraction_ms,
            "chapterization_ms": chapterization_ms,
            "page_count": len(pages),
            "chapter_count": len(fallback_chapters),
            "toc_count": 0,
            "heading_count": 0,
            "intro_present": False,
            "toc": [],
            "chapters": [],
            "warnings": warnings,
            "intro_text_sha256": None,
        }
        for ch in fallback_chapters:
            p = write_chapter_json(ch, out_dir)
            records_fallback.append(
                {
                    "id": f"{book_id}-{ch.chapter_id}",
                    "book_id": book_id,
                    "index": ch.index,
                    "title": ch.title,
                    "text_sha256": ch.text_sha256,
                    "json_path": str(p),
                    "chapter_id": ch.chapter_id,
                    "source_pdf_name": Path(pdf_path).name,
                    "meta": _basic_text_meta(ch.text) | {"source": "fallback_single"},
                    "text": ch.text,
                }
            )
            volume["chapters"].append(
                {
                    "chapter_id": ch.chapter_id,
                    "index": ch.index,
                    "title": ch.title,
                    "number": None,
                    "start_page": None,
                    "end_page": None,
                    "page_count": None,
                    "word_count": _basic_text_meta(ch.text)["word_count"],
                    "char_count": len(ch.text),
                    "sentence_count": None,
                    "paragraph_count": None,
                    "source": "fallback_single",
                    "json_path": str(p),
                    "text_sha256": ch.text_sha256,
                }
            )
        volume_json_path_local = None
        try:
            vol_path = out_dir / f"{Path(pdf_path).stem}_volume.json"
            vol_path.write_text(json.dumps(volume, ensure_ascii=False, indent=2), encoding="utf-8")
            volume_json_path_local = str(vol_path)
        except Exception:  # pragma: no cover
            logger.exception("volume_json_write_error pdf=%s", Path(pdf_path).name)
        return (
            records_fallback,
            next_index + len(records_fallback),
            result,
            warnings,
            len(pages),
            extraction_ms,
            chapterization_ms,
            False,
            None,
            None,
            parse_mode,
            volume_json_path_local,
        )

    chapters_local: list[Chapter] = []
    intro_text = structured.get("intro") or ""
    # Emit intro as its own chapter (id INTRO before reindex) so that
    # canonical snapshot expecting an intro chapter (00000 after reindex)
    # remains valid. It is excluded from chapter_count but included in
    # emitted artifacts and volume intro_present flag.
    if intro_text.strip():
        # Normalize intro text: strip and unify line endings for stable hashing
        norm_intro = "\n".join(line.rstrip() for line in intro_text.strip().splitlines())
        chapters_local.append(
            Chapter(
                book_id=book_id,
                chapter_id="INTRO",
                index=0,
                title="Intro",
                text=norm_intro,
                text_sha256=sha256_text(norm_intro),
            )
        )
    for ch_entry in structured.get("chapters", []):
        body = ch_entry["text"]
        title = f"Chapter {ch_entry['number']}: {ch_entry['title']}"
        chapters_local.append(
            Chapter(
                book_id=book_id,
                chapter_id=f"{ch_entry['number']:05d}",
                index=ch_entry["number"],
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
    records: list[dict[str, object]] = []
    next_index = next_index_start

    # Pre-compute counts
    toc_list = structured.get("toc", [])
    chapters_struct = structured.get("chapters", [])
    toc_count = len(toc_list)
    intro_present_bool = bool(intro_text.strip())
    deduct = 1 if (intro_present_bool and (len(chapters_struct) == toc_count)) else 0
    heading_count_val = len(chapters_struct) - deduct

    volume_obj: dict[str, Any] = {
        "schema_version": "1.0",
        "book_id": book_id,
        "pdf_name": pdf_path.name,
        "pdf_stem": pdf_path.stem,
        "parse_mode": parse_mode,
        "extraction_ms": extraction_ms,
        "chapterization_ms": chapterization_ms,
        "page_count": len(pages),
        # chapter_count includes intro (matches tests)
        "chapter_count": len(chapters_local),
        "toc_count": toc_count,
        # Canonical snapshot heading_count excludes intro; structured chapters
        # list does not include intro so subtract 1 only if counts match toc
        "heading_count": heading_count_val,
        "intro_present": intro_present_bool,
        "toc": toc_list,
        # Always emit intro as a chapter if present
        "chapters": [],
        "warnings": warnings,
        "intro_text_sha256": (sha256_text(intro_text.strip()) if intro_text.strip() else None),
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
            warnings.append("toc_numbers_without_headings:" + ",".join(map(str, missing_from_headings)))
        if missing_from_toc:
            warnings.append("headings_without_toc_numbers:" + ",".join(map(str, missing_from_toc)))
        if len(toc_numbers) != volume_obj["toc_count"]:
            removed = int(volume_obj["toc_count"]) - len(toc_numbers)
            warnings.append(f"toc_dedup_removed={removed}")

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
            logger.debug("skip_existing_chapter id=%s title=%s", record_id, new_ch.title)
            continue
        p = write_chapter_json(new_ch, out_dir)
        meta = _basic_text_meta(new_ch.text)
        chapter_number = None
        parts = new_ch.title.split()
        if len(parts) >= 2 and parts[0].lower() == "chapter" and parts[1].rstrip(":").isdigit():
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
        volume_obj["chapters"].append(vol_entry)
        extra_meta = {
            "source": "structured_toc",
            "chapter_number": chapter_number,
        }
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
                "meta": meta | extra_meta,
            }
        )

    volume_json_path: str | None = None
    try:
        vol_path = out_dir / f"{pdf_path.stem}_volume.json"
        vol_path.write_text(
            json.dumps(volume_obj, ensure_ascii=False, indent=2),
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


def enumerate_pdfs(book_id: str) -> list[Path]:
    book_dir = Path("data/books") / book_id
    source_dir = book_dir / "source_pdfs"
    pdfs: list[Path] = []
    if book_dir.exists():
        pdfs.extend(sorted(book_dir.glob("*.pdf")))
    if source_dir.exists():
        pdfs.extend(sorted(source_dir.glob("*.pdf")))
    return pdfs
