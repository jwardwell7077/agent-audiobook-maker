"""Minimal, deterministic Section Classifier stub.

This provides a contract-satisfying function `classify_sections` that
constructs placeholder artifacts with empty/warning-only content. It lets
us wire up APIs and tests before heuristics are implemented.

See docs/SECTION_CLASSIFIER_SPEC.md for details.
"""

from __future__ import annotations

import re
from hashlib import sha256

from abm.classifier.types import (
    TOC,
    BackMatter,
    ChaptersSection,
    ClassifierInputs,
    ClassifierOutputs,
    DocumentMeta,
    FrontMatter,
    Page,
    PageMarker,
    PerPageLabel,
    TOCEntry,
)

_NUM_ONLY_RE = re.compile(r"^(?:page\s+)?(\d{1,4})$", re.IGNORECASE)
_ROMAN_ONLY_RE = re.compile(r"^(?=.{2,}$)[IVXLCDM]+$", re.IGNORECASE)
_INLINE_TRAIL_NUM_RE = re.compile(
    r"^(?P<prefix>.*?)\s*(?:[-–—•\s]+)?(?:(?:page\s+)?(?P<num>\d{1,4}))\s*$",
    re.IGNORECASE,
)

_TOC_HEADING_RE = re.compile(
    r"^\s*(table of contents|contents)\s*$",
    re.IGNORECASE,
)
_TOC_LINE_ENDS_NUM_RE = re.compile(r"\d{1,4}\s*$")
_TOC_DOTS_RE = re.compile(r"\.{2,}\s*\d{1,4}$")


def _is_page_number_only(text: str) -> str | None:
    """Return normalized page number string if line is a page-number-only line.

    Supports simple numeric forms (e.g., "12", "Page 12") and Roman numerals
    (at least two chars) on a line by themselves.
    """

    s = text.strip()
    m = _NUM_ONLY_RE.match(s)
    if m:
        return m.group(1)
    if _ROMAN_ONLY_RE.match(s):
        return s.upper()
    return None


def _strip_inline_trailing_page_number(text: str) -> tuple[str, str | None]:
    """Strip a trailing page-number token from a content line if present.

    Returns (cleaned_line, number_value or None). Only numeric trailing tokens
    like "... 12" or "... Page 12" are stripped. Roman numerals are not
    handled here to avoid removing valid headings like "Chapter IV".
    """

    s = text.rstrip()
    m = _INLINE_TRAIL_NUM_RE.match(s)
    if not m:
        return text, None
    prefix = m.group("prefix") or ""
    num = m.group("num")
    if not prefix.strip():
        # This is likely a page-number-only line; do not strip here.
        return text, None
    return prefix.rstrip(), num


def _build_body_and_markers(
    pages: list[Page],
) -> tuple[list[tuple[int, str]], list[PageMarker]]:
    """Return flattened cleaned lines with page indices and page markers.

    - Remove page-number-only lines and record a marker.
    - For inline trailing numbers, strip the token and record a marker.
    Returns:
        flat_lines: [(page_index, cleaned_line), ...]
        markers: list of PageMarker
    """

    flat_lines: list[tuple[int, str]] = []
    markers: list[PageMarker] = []
    global_line_index = 0

    for page in pages:
        for line in page.lines:
            only = _is_page_number_only(line)
            if only is not None:
                markers.append(
                    {
                        "page_index": page.page_index,
                        "line_index_global": global_line_index,
                        "value": only,
                    }
                )
                # Do not add the line; do not advance global_line_index
                continue

            cleaned, num = _strip_inline_trailing_page_number(line)
            if num is not None:
                markers.append(
                    {
                        "page_index": page.page_index,
                        "line_index_global": global_line_index,
                        "value": num,
                    }
                )
            flat_lines.append((page.page_index, cleaned))
            global_line_index += 1

    return flat_lines, markers


def _detect_toc_pages(pages: list[Page]) -> list[int]:
    """Heuristic detection of TOC pages.

    Signals:
    - Presence of a heading line "Contents" or "Table of Contents".
    - Many short lines ending with numbers and/or dotted leaders.
    """

    toc_pages: list[int] = []
    for page in pages:
        lines = page.lines
        if any(_TOC_HEADING_RE.match(ln or "") for ln in lines):
            toc_pages.append(page.page_index)
            continue

        candidates = 0
        dots = 0
        for ln in lines:
            if len(ln) > 120:
                continue
            if _TOC_LINE_ENDS_NUM_RE.search(ln or ""):
                candidates += 1
            if _TOC_DOTS_RE.search(ln or ""):
                dots += 1
        total = len(lines) or 1
        ratio = candidates / total
        if candidates >= 3 and (ratio >= 0.3 or dots >= 2):
            toc_pages.append(page.page_index)
    return sorted(set(toc_pages))


_TOC_ENTRY_RE = re.compile(
    r"^(?P<title>.+?)\s*(?:\.{2,}|\s{2,}|[-–—•\s]{2,})?\s*(?P<page>\d{1,4})$"
)


def _parse_toc_entries(
    pages: list[Page], toc_pages: list[int]
) -> list[TOCEntry]:
    """Parse basic TOC entries from the detected TOC pages."""

    entries: list[TOCEntry] = []
    toc_set = set(toc_pages)
    for page in pages:
        if page.page_index not in toc_set:
            continue
        for i, raw in enumerate(page.lines):
            s = raw.strip()
            if not s:
                continue
            m = _TOC_ENTRY_RE.match(s)
            if not m:
                continue
            title = m.group("title").strip()
            # Reject titles that are too short after stripping
            if not title or title.isdigit():
                continue
            try:
                page_no = int(m.group("page"))
            except ValueError:
                continue
            entries.append(
                {
                    "title": title,
                    "page": page_no,
                    "raw": raw,
                    "line_in_toc": i,
                }
            )
    return entries


def classify_sections(inputs: ClassifierInputs) -> ClassifierOutputs:
    """Classify book sections and return four artifacts.

        This stub returns deterministic, minimal artifacts:
        - span values cover the entire concatenated text (0..N chars) based on
            joined lines.
    - text_sha256 is computed from the joined text for front/back placeholders.
    - toc contains no entries.
    - per_page_labels marks all pages as "body" with confidence 0.0.
    - warnings explain that this is a stub.
    """

    pages = inputs.get("pages", [])
    flat_lines, page_markers = _build_body_and_markers(pages)
    body_lines = [ln for _, ln in flat_lines]
    joined = "\n".join(body_lines)
    text_hash = sha256(joined.encode("utf-8")).hexdigest()

    # overall length of cleaned joined text
    total_len = len(joined)

    # Compute per-page char spans using flattened lines and joined text.
    page_spans: dict[int, tuple[int, int]] = {}
    char_pos = 0
    for idx, (pg_idx, line) in enumerate(flat_lines):
        start = char_pos
        end = start + len(line)
        if pg_idx not in page_spans:
            page_spans[pg_idx] = (start, end)
        else:
            # expand existing span
            cur_s, cur_e = page_spans[pg_idx]
            page_spans[pg_idx] = (min(cur_s, start), max(cur_e, end))
        # advance for newline except after last line
        if idx < len(flat_lines) - 1:
            char_pos = end + 1
        else:
            char_pos = end

    # Derive coarse section spans:
    # chapters_section covers all body; others are before/after.
    if page_spans:
        first_body_start = min(s for s, _ in page_spans.values())
        last_body_end = max(e for _, e in page_spans.values())
        span_front = [0, first_body_start]
        span_body = [first_body_start, last_body_end]
        span_back = [last_body_end, total_len]
    else:
        span_front = [0, 0]
        span_body = [0, 0]
        span_back = [0, 0]
    span_toc = [0, 0]

    document_meta: DocumentMeta = {"page_markers": page_markers}

    front: FrontMatter = {
        "span": span_front,
        "text_sha256": text_hash,
        "warnings": [
            "page-number-only lines removed; inline trailing numbers stripped",
        ],
        "document_meta": document_meta,
    }

    # TOC detection and span
    toc_pages = _detect_toc_pages(pages)
    toc_entries = _parse_toc_entries(pages, toc_pages)
    if toc_pages and page_spans:
        starts = []
        ends = []
        for pidx in toc_pages:
            if pidx in page_spans:
                s, e = page_spans[pidx]
                starts.append(s)
                ends.append(e)
        if starts and ends:
            span_toc = [min(starts), max(ends)]
    toc_warnings: list[str] = []
    if not toc_entries:
        toc_warnings.append("no toc entries parsed")
    else:
        toc_warnings.append(
            f"parsed {len(toc_entries)} entries from {len(set(toc_pages))} toc page(s)"
        )
    toc: TOC = {
        "span": span_toc,
        "entries": toc_entries,
        "warnings": toc_warnings,
    }

    per_page: list[PerPageLabel] = [
        {"page_index": p.page_index, "label": "body", "confidence": 0.0}
        for p in pages
    ]
    chapters_section: ChaptersSection = {
        "span": span_body,
        "per_page_labels": per_page,
        "warnings": ["stub: all pages labeled body with 0.0 confidence"],
    }

    back: BackMatter = {
        "span": span_back,
        "text_sha256": text_hash,
        "warnings": ["stub: identical to front for placeholder"],
    }

    return {
        "front_matter": front,
        "toc": toc,
        "chapters_section": chapters_section,
        "back_matter": back,
    }
