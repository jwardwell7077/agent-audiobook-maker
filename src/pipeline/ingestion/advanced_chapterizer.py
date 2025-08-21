r"""Advanced chapter parsing using Table of Contents + heading markers.

Keeps existing simple_chapterize untouched; this module adds a higher
fidelity splitter for large multi-chapter PDFs (hundreds/thousands of
chapters) that follow a pattern:

  <front matter>
  Table of Contents
  • Chapter 1: Title
  • Chapter 2: Title Two
  ...
  Chapter 1: Title
  <chapter text>
  Chapter 2: Title Two
  <chapter text>

Strategy:
  * Identify TOC section (line containing 'Table of Contents').
  * Collect bullet lines or plain lines mapping chapter number -> title.
    * Parse full text for heading lines ^Chapter\\s+N: Title
    * Verify counts match TOC (else raise ValueError for caller to fallback).
    * Produce Chapter objects + metadata (word/char/sentence/paragraph/page
        counts).

Page mapping:
  We approximate page ranges by reconstructing cumulative character
  offsets per page (from extract_pdf_text.pages order). For each chapter
  span (start_offset:end_offset) we compute which pages overlap.

Public entry point: attempt_advanced_chapterize(book_id, full_text, pages)
returns list[ChapterWithMeta] or raises ValueError on low confidence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .chapterizer import Chapter, sha256_text


@dataclass(frozen=True)
class ChapterWithMeta(Chapter):
    """Chapter model enriched with computed metadata.

    Metadata keys:
    word_count / char_count / sentence_count / paragraph_count
    page_count / start_page / end_page (if page info provided)
    source: origin of strategy (advanced_toc | heading_only)
    chapter_number: 1-based ordinal parsed from heading / TOC
    """

    meta: dict[str, Any]


HEADING_RE = re.compile(r"^Chapter\s+(\d{1,5})\s*:?\s*(.+)$", re.IGNORECASE)
TOC_LINE_RE = re.compile(r"Chapter\s+(\d{1,5})\s*:?\s*(.+)")


def _split_lines(text: str) -> list[str]:
    return text.replace("\r", "").splitlines()


def _find_toc_indices(lines: Sequence[str]) -> int | None:
    for i, line in enumerate(lines):
        low = line.lower().strip()
        if "table of contents" in low:
            return i
        # Accept a standalone "contents" line as TOC start fallback
        if low == "contents":  # broader compatibility
            return i
    return None


def _parse_toc(lines: Sequence[str], start: int) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for line in lines[start + 1 : start + 1 + 2000]:  # scan ahead
        if not line.strip():
            # allow blank lines inside TOC
            continue
        raw = line.strip().lstrip("• ")
        m = TOC_LINE_RE.search(raw)
        if not m:
            # Heuristic: stop when pattern breaks after some entries
            if entries:
                # break on first non-matching line after we started
                if raw.lower().startswith("chapter 1"):
                    # might be body start; keep scanning few lines
                    continue
                break
            else:
                continue
        num = int(m.group(1))
        title = m.group(2).strip()
        entries.append((num, title))
    # Deduplicate in case of repeats
    seen = set()
    deduped: list[tuple[int, str]] = []
    for n, t in entries:
        if n in seen:
            continue
        seen.add(n)
        deduped.append((n, t))
    return deduped


def _find_headings(lines: Sequence[str]) -> list[tuple[int, int, str]]:
    matches: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        m = HEADING_RE.match(line.strip())
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            matches.append((idx, num, title))
    return matches


def _sentence_count(text: str) -> int:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    return len(sentences)


def _paragraph_count(text: str) -> int:
    return len([p for p in text.split("\n\n") if p.strip()])


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _compute_page_offsets(pages: Sequence[str]) -> list[tuple[int, int, int]]:
    offsets: list[tuple[int, int, int]] = []
    cursor = 0
    for i, page in enumerate(pages):
        start = cursor
        cursor += len(page)
        offsets.append((i, start, cursor))
    return offsets


def _pages_for_span(
    start: int,
    end: int,
    page_offsets: Sequence[tuple[int, int, int]],
) -> tuple[int, int, int]:
    page_indices = [pi for (pi, s, e) in page_offsets if not (e <= start or s >= end)]
    if not page_indices:
        return (0, 0, 0)
    return (len(page_indices), min(page_indices), max(page_indices))


def attempt_advanced_chapterize(
    book_id: str,
    full_text: str,
    pages: Sequence[str] | None = None,
    min_chapters: int = 20,
) -> list[ChapterWithMeta]:
    """Try high-fidelity chapter parsing; raise ValueError if low confidence.

    min_chapters: if fewer headings than this, treat as low benefit and
    fail fast.
    """
    lines = _split_lines(full_text)
    toc_idx = _find_toc_indices(lines)
    if toc_idx is None:
        raise ValueError("No Table of Contents marker found")
    toc_entries = _parse_toc(lines, toc_idx)
    if not toc_entries or len(toc_entries) < min_chapters:
        raise ValueError("TOC entries below threshold")
    headings = _find_headings(lines)
    if len(headings) < min_chapters:
        raise ValueError("Heading count below threshold")
    heading_by_num: dict[int, tuple[int, str]] = {}
    for line_idx, num, title in headings:
        heading_by_num.setdefault(num, (line_idx, title))
    missing = [n for (n, _t) in toc_entries if n not in heading_by_num]
    if missing:
        raise ValueError(f"Missing chapter headings for numbers: {missing[:5]}")
    ordered_numbers = [n for (n, _t) in toc_entries]
    seen: set[int] = set()
    deduped: list[int] = []
    for n in ordered_numbers:
        if n not in seen:
            seen.add(n)
            deduped.append(n)
    ordered_numbers = deduped
    page_offsets = _compute_page_offsets(pages) if pages else []
    joined = "\n".join(lines)
    line_starts: list[int] = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1
    chapters: list[ChapterWithMeta] = []
    for i, num in enumerate(ordered_numbers):
        line_idx, title = heading_by_num[num]
        start_char = line_starts[line_idx]
        if i + 1 < len(ordered_numbers):
            next_line_idx, _ = heading_by_num[ordered_numbers[i + 1]]
            end_char = line_starts[next_line_idx]
        else:
            end_char = len(joined)
        raw_text = joined[start_char:end_char].strip()
        text_sha = sha256_text(raw_text)
        wc = _word_count(raw_text)
        cc = len(raw_text)
        sc = _sentence_count(raw_text)
        pc = _paragraph_count(raw_text)
        (page_count, start_page, end_page) = (
            _pages_for_span(start_char, end_char, page_offsets) if page_offsets else (0, 0, 0)
        )
        chapter_id = f"{(num - 1):05d}"
        meta = {
            "word_count": wc,
            "char_count": cc,
            "sentence_count": sc,
            "paragraph_count": pc,
            "page_count": page_count,
            "start_page": start_page,
            "end_page": end_page,
            "source": "advanced_toc",
            "chapter_number": num,
        }
        chapters.append(
            ChapterWithMeta(
                book_id=book_id,
                chapter_id=chapter_id,
                index=num - 1,
                title=title,
                text=raw_text,
                text_sha256=text_sha,
                meta=meta,
            )
        )
    return chapters


def heading_only_chapterize(
    book_id: str,
    full_text: str,
    pages: Sequence[str] | None = None,
    min_headings: int = 2,
) -> list[ChapterWithMeta]:
    """Fallback splitter using only heading lines ("Chapter N: Title").

    Produces chapters in heading order without TOC validation. Useful when
    a PDF lacks a recognizable TOC marker but still has clear chapter
    headings.
    Raises ValueError if insufficient headings found.
    """
    lines = _split_lines(full_text)
    headings = _find_headings(lines)
    if len(headings) < min_headings:
        raise ValueError("Insufficient headings for heading-only mode")
    # Build offsets like advanced
    joined = "\n".join(lines)
    line_starts: list[int] = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1
    page_offsets = _compute_page_offsets(pages) if pages else []
    chapters: list[ChapterWithMeta] = []
    for i, (line_idx, num, title) in enumerate(headings):
        start_char = line_starts[line_idx]
        if i + 1 < len(headings):
            next_line_idx, _next_num, _next_title = headings[i + 1]
            end_char = line_starts[next_line_idx]
        else:
            end_char = len(joined)
        raw_text = joined[start_char:end_char].strip()
        text_sha = sha256_text(raw_text)
        wc = _word_count(raw_text)
        cc = len(raw_text)
        sc = _sentence_count(raw_text)
        pc = _paragraph_count(raw_text)
        (page_count, start_page, end_page) = (
            _pages_for_span(start_char, end_char, page_offsets) if page_offsets else (0, 0, 0)
        )
        chapter_id = f"{(num - 1):05d}"
        meta = {
            "word_count": wc,
            "char_count": cc,
            "sentence_count": sc,
            "paragraph_count": pc,
            "page_count": page_count,
            "start_page": start_page,
            "end_page": end_page,
            "source": "heading_only",
            "chapter_number": num,
        }
        chapters.append(
            ChapterWithMeta(
                book_id=book_id,
                chapter_id=chapter_id,
                index=num - 1,
                title=title,
                text=raw_text,
                text_sha256=text_sha,
                meta=meta,
            )
        )
    return chapters


def write_chapter_json_with_meta(ch: ChapterWithMeta, out_dir: Path) -> Path:
    """Write a chapter (with meta) to ``out_dir`` as ``<chapter_id>.json``.

    Returns the path of the written file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{ch.chapter_id}.json"
    payload = {
        "book_id": ch.book_id,
        "chapter_id": ch.chapter_id,
        "index": ch.index,
        "title": ch.title,
        "text": ch.text,
        "text_sha256": ch.text_sha256,
        "meta": ch.meta,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
