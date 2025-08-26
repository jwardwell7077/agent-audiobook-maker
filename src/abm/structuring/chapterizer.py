"""Deterministic Chapterizer using TOC titles and cleaned body text.

Algorithm per docs/CHAPTERIZER_SPEC.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from abm.classifier.section_classifier import (
    _build_body_and_markers,  # reuse cleaning logic
    classify_sections,
)
from abm.classifier.types import ClassifierInputs, Page, TOCEntry
from abm.ingestion.txt_to_structured_json import parse_paragraphs


class Chapter(TypedDict):
    index: int
    title: str
    start_char: int
    end_char: int
    paragraphs: list[str]


class ChapterizerOutput(TypedDict):
    version: str
    created_at: str
    chapters: list[Chapter]
    unmatched_titles: list[str]
    duplicate_title_matches: list[dict]
    warnings: list[str]


@dataclass(frozen=True)
class BodySlice:
    text: str
    start: int
    end: int


def _split_pages(text: str) -> list[str]:
    """Split input text into pages by form-feed or double newlines.

    Prefers form-feed (\f) separators. Strips trailing whitespace per page.
    """
    if "\f" in text:
        parts = text.split("\f")
    else:
        parts = text.split("\n\n")
    return [p.strip("\n\r ") for p in parts]


def _to_pages(raw_pages: Iterable[str]) -> list[Page]:
    """Convert raw page strings into classifier Page objects."""
    pages: list[Page] = []
    for i, p in enumerate(raw_pages):
        lines = p.splitlines() if p else []
        pages.append(Page(page_index=i + 1, lines=lines))
    return pages


def _normalize_line(s: str) -> str:
    """Normalize a line by trimming and collapsing whitespace to lower-case."""
    return " ".join((s or "").strip().split()).lower()


def _int_to_roman(n: int) -> str:
    """Convert integer to uppercase Roman numeral."""
    vals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out: list[str] = []
    x = n
    for v, sym in vals:
        while x >= v:
            out.append(sym)
            x -= v
    return "".join(out)


def _fallback_titles(idx_one_based: int) -> list[str]:
    """Generate numeric/roman fallback title patterns for a chapter index."""
    n = idx_one_based
    roman = _int_to_roman(n)
    return [
        f"chapter {n}",
        f"ch {n}",
        f"ch. {n}",
        f"chapter {roman}",
        roman,
    ]


def _find_line_positions(
    body_slice: BodySlice, titles: list[str]
) -> tuple[list[int], list[str], list[dict], list[str]]:
    """Find absolute start positions for chapter titles within a body slice.

    Returns a tuple of:
    - start_positions
    - unmatched_titles
    - duplicate_title_matches
    - warnings
    """
    # Build line index with char start offsets within the slice
    lines = body_slice.text.splitlines()
    offsets: list[int] = []
    pos = 0
    for i, ln in enumerate(lines):
        offsets.append(pos)
        if i < len(lines) - 1:
            pos += len(ln) + 1
        else:
            pos += len(ln)

    norm_lines = [_normalize_line(ln) for ln in lines]

    starts: list[int] = []
    unmatched: list[str] = []
    duplicates: list[dict] = []
    warnings: list[str] = []

    for i, raw_title in enumerate(titles, start=1):
        norm_title = _normalize_line(raw_title)
        matches = [j for j, line in enumerate(norm_lines) if line == norm_title]
        if len(matches) == 0:
            # attempt fallback
            fb = _fallback_titles(i)
            fb_norm = [_normalize_line(x) for x in fb]
            fb_matches: list[int] = []
            for j, line in enumerate(norm_lines):
                if line in fb_norm:
                    fb_matches.append(j)
            if fb_matches:
                warnings.append(f"fallback used for title index {i}: '{raw_title}'")
                matches = fb_matches
            else:
                unmatched.append(raw_title)
                continue
        # If a title appears on 5 or more separate lines within the body slice,
        # treat it as an ambiguous duplicate signal and abort upstream.
        if len(matches) >= 5:
            duplicates.append({"title": raw_title, "count": len(matches)})
            continue
        if len(matches) > 1:
            warnings.append(f"title '{raw_title}' matched {len(matches)} lines; using first occurrence")
        line_idx = matches[0]
        starts.append(body_slice.start + offsets[line_idx])

    return starts, unmatched, duplicates, warnings


def _slice_chapters(
    body_text: str,
    start_points: list[int],
    body_span: tuple[int, int],
    titles: list[str],
) -> list[Chapter]:
    """Build chapter objects from sorted start points and titles."""
    if not start_points:
        return []
    starts_sorted = sorted(set(start_points))
    chapters: list[Chapter] = []
    for idx, abs_start in enumerate(starts_sorted):
        abs_end = starts_sorted[idx + 1] if idx + 1 < len(starts_sorted) else body_span[1]
        title = titles[idx] if idx < len(titles) else f"Chapter {idx + 1}"
        # Extract chapter slice and split into paragraphs (by blank lines)
        chapter_text = body_text[abs_start:abs_end]
        paragraphs = parse_paragraphs(chapter_text)
        chapters.append(
            {
                "index": idx + 1,
                "title": title,
                "start_char": abs_start,
                "end_char": abs_end,
                "paragraphs": paragraphs,
            }
        )
    return chapters


_HEADING_RE = re.compile(
    (
        r"^\s*(?:chapter|ch)\s+(?P<num>[0-9IVXLCDM]+)\s*"
        r"[:.\-–—]?\s*(?P<title>.+?)\s*$"
    ),
    re.IGNORECASE,
)


def _scan_body_headings(body_slice: BodySlice) -> list[tuple[int, str]]:
    """Scan body lines for chapter headings and return (abs_pos, title).

    Matches patterns like:
    - "Chapter 1: Just an old Book"
    - "CH 2 - Daily Quest"
    - "Chapter IV. Title"
    """
    lines = body_slice.text.splitlines()
    # compute offsets for each line start within slice
    offsets: list[int] = []
    pos = 0
    for i, ln in enumerate(lines):
        offsets.append(pos)
        pos += len(ln) + (1 if i < len(lines) - 1 else 0)

    found: list[tuple[int, str]] = []
    for i, raw in enumerate(lines):
        m = _HEADING_RE.match(raw.strip())
        if not m:
            continue
        title_part = m.group("title").strip()
        num = m.group("num").strip()
        if not title_part:
            continue
        # Normalize combined title text
        title = f"Chapter {num}: {title_part}"
        abs_pos = body_slice.start + offsets[i]
        found.append((abs_pos, title))
    return found


def chapterize_from_text(input_txt: Path) -> ChapterizerOutput:
    """Run chapterization on a cleaned text file and return the output dict."""
    # Read and clean
    text = input_txt.read_text(encoding="utf-8")
    raw_pages = _split_pages(text)
    pages = _to_pages(raw_pages)

    # Build cleaned body text exactly like classifier
    flat_lines, _ = _build_body_and_markers(pages)
    body_lines = [ln for _, ln in flat_lines]
    body_text = "\n".join(body_lines)

    # Get toc and spans from classifier
    # Build classifier inputs (TypedDict) and classify
    inputs: ClassifierInputs = {"pages": pages}
    outputs = classify_sections(inputs)
    toc_entries: list[TOCEntry] = outputs["toc"]["entries"]  # type: ignore
    span_body_list = outputs["chapters_section"]["span"]  # type: ignore[index]
    body_span = (int(span_body_list[0]), int(span_body_list[1]))

    # Extract titles in order
    titles = [e["title"] for e in toc_entries]

    # Bounds check
    body_span = (max(0, body_span[0]), min(len(body_text), body_span[1]))
    slice_obj = BodySlice(
        text=body_text[body_span[0] : body_span[1]],
        start=body_span[0],
        end=body_span[1],
    )

    starts: list[int] = []
    unmatched: list[str] = []
    duplicates: list[dict] = []
    warns: list[str] = []

    if titles:
        s, u, d, w = _find_line_positions(slice_obj, titles)
        starts, unmatched, duplicates, warns = s, u, d, w

    # If no TOC titles or no matches found, try body heading fallback
    if (not titles) or (titles and not starts):
        headings = _scan_body_headings(slice_obj)
        if headings:
            headings_sorted = sorted(headings, key=lambda x: x[0])
            starts = [p for p, _ in headings_sorted]
            titles = [t for _, t in headings_sorted]
            warns.append(f"body_heading_fallback used: {len(headings_sorted)} chapters")

    # Abort conditions
    if duplicates:
        return {
            "version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "chapters": [],
            "unmatched_titles": unmatched,
            "duplicate_title_matches": duplicates,
            "warnings": ["aborted: duplicate title matched >5 lines"] + warns,
        }
    if titles:
        unmatched_ratio = (len(unmatched) / len(titles)) if titles else 1.0
        if unmatched_ratio > 0.4:
            return {
                "version": "1.0",
                "created_at": datetime.now(UTC).isoformat(),
                "chapters": [],
                "unmatched_titles": unmatched,
                "duplicate_title_matches": duplicates,
                "warnings": ["aborted: too many unmatched titles (>40%)"] + warns,
            }

    chapters = _slice_chapters(body_text, starts, body_span, titles)
    return {
        "version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "chapters": chapters,
        "unmatched_titles": unmatched,
        "duplicate_title_matches": duplicates,
        "warnings": warns,
    }


def write_chapters_json(out_path: Path, data: ChapterizerOutput) -> None:
    """Write chapterizer output JSON to ``out_path`` (UTF-8, pretty)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
