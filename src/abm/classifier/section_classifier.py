from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

TOC_HEADING_RE = re.compile(r"^\s*(table of contents|contents)\b", re.I)
BULLET = r"[\u2022\-\*]?"  # • - * optional
ORDINAL = r"(?:chapter\s+(?P<digits>\d+)|prologue|epilogue)"
SEPARATOR = r"[\s:\.-]*"
TITLE_CAPTURE = r"(?P<title>.+?)\s*$"
TOC_ITEM_RE_STRICT = re.compile(rf"^\s*{BULLET}\s*{ORDINAL}{SEPARATOR}{TITLE_CAPTURE}", re.I)
# Within the TOC span, accept lines with optional ordinal tokens followed by a title
TOC_ITEM_RE_LOOSE = re.compile(rf"^\s*{BULLET}\s*(?:(?:{ORDINAL}{SEPARATOR})\s*)?{TITLE_CAPTURE}", re.I)
# Fallback pattern: accept dotted leaders and optional trailing page numbers
TOC_ITEM_RE_FALLBACK = re.compile(
    r"^\s*[\u2022\-\*]?\s*(?:"  # optional bullet
    r"(?:(?:Chapter\s+(?P<digits_fb>\d+))|Prologue|Epilogue)[:\s\.-]*)?"  # optional ordinal prefix
    r"(?P<title_fb>.+?)\s*"  # title
    r"(?:\.{2,}\s*\d+)?\s*$",  # optional dotted leaders + page number
    re.I,
)
BODY_HEADING_RE = re.compile(
    (
        r"^\s*"
        r"(?:(?:Chapter\s+(?P<digits>\d+))|(?P<pro>Prologue)|(?P<epi>Epilogue))"
        r"\s*(?::|\.|\-|\s)?\s*"
        r"(?P<title>[^\n]*)\s*$"
    ),
    re.I,
)

# Heuristics for heading candidates using enriched JSONL fields
MAX_HEADING_WORDS = 12
MAX_HEADING_CHARS = 80


def canon_title(s: str) -> str:
    norm = unicodedata.normalize("NFKD", s)
    no_marks = "".join(ch for ch in norm if not unicodedata.combining(ch))
    lowered = no_marks.lower()
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    collapsed = re.sub(r"\s+", " ", cleaned).strip()
    return collapsed


def _load_jsonl_blocks(path: str) -> list[dict[str, Any]]:
    if not path.endswith(".jsonl"):
        raise ValueError("Input must be a .jsonl file")
    blocks: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip("\n")
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSONL at line {ln}: {e}") from e
            if not isinstance(obj, dict) or "text" not in obj or not isinstance(obj["text"], str):
                raise ValueError(f"Invalid JSONL record at line {ln}: expected object with text:string")
            blocks.append(obj)
    if not blocks:
        raise ValueError("No valid blocks found in JSONL")
    if all(isinstance(b.get("index"), int) for b in blocks):
        blocks.sort(key=lambda b: int(b["index"]))
    return blocks


def _find_toc_heading(blocks: list[dict[str, Any]]) -> int:
    saw_heading = False
    for i, b in enumerate(blocks):
        if TOC_HEADING_RE.search(b["text"]):
            saw_heading = True
            ahead = blocks[i + 1 : i + 6]
            # Keep strict lookahead to avoid false positives
            count = sum(1 for a in ahead if TOC_ITEM_RE_STRICT.search(a["text"]))
            if count >= 2:
                return i
            else:
                break
    if saw_heading:
        raise ValueError("TOC heading found but no TOC items ahead")
    raise ValueError("TOC heading not found")


def _parse_toc_items(
    blocks: list[dict[str, Any]], start_idx: int, end_idx: int | None = None
) -> tuple[list[dict[str, Any]], int, list[str]]:
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    # We no longer dedupe by canonical title; duplicates can be legitimate
    last_text: str | None = None
    seen_ord: dict[int, str] = {}
    last_item_block = start_idx
    i = start_idx + 1
    # Heuristics to avoid picking non-TOC lines in the TOC span
    MAX_TOC_WORDS = 30
    MAX_TOC_CHARS = 150
    limit = end_idx if isinstance(end_idx, int) else len(blocks)
    while i < len(blocks) and i < limit:
        blk = blocks[i]
        # Skip multi-line or very long blocks which are unlikely to be single TOC items
        lc = blk.get("line_count")
        wc = blk.get("word_count")
        cc = blk.get("char_count")
        if (
            (isinstance(lc, int) and lc > 2)
            or (isinstance(wc, int) and wc > MAX_TOC_WORDS)
            or (isinstance(cc, int) and cc > MAX_TOC_CHARS)
        ):
            i += 1
            continue
        text = blk.get("text", "").strip()
        m = TOC_ITEM_RE_STRICT.match(text)
        if not m:
            # Try fallback only if it resembles a typical TOC line with dotted leaders
            m2 = TOC_ITEM_RE_FALLBACK.match(text)
            dotted = bool(re.search(r"\.{2,}\s*\d+\s*$", text))
            if not m2 or not dotted:
                i += 1
                continue
            title = (m2.group("title_fb") or "").strip()
            digits = m2.group("digits_fb")
        else:
            title = (m.group("title") or "").strip()
            digits = m.group("digits")
        # Clean up TOC title: drop dotted leaders and trailing page numbers if present
        if title:
            title = re.sub(r"\.{2,}\s*\d+\s*$", "", title).strip()
        # Filter out lines that look like numeric-only sequences (e.g., '1..2..3..4..5')
        canon_no_space = re.sub(r"\s+", "", canon_title(title))
        digits_only_pattern = re.compile(r"^(?:\d+[\.]*)+$")
        has_letters = bool(re.search(r"[A-Za-z]", title))
        if not has_letters and (digits is None):
            i += 1
            continue
        if canon_no_space and digits_only_pattern.match(canon_no_space):
            i += 1
            continue
        ordinal = int(digits) if digits else None
        ctitle = canon_title(title)
        # Skip only immediate exact duplicate lines to avoid double-capture
        if last_text is not None and text == last_text:
            warnings.append(f"immediate duplicate TOC line skipped at block {i}")
            i += 1
            continue
        if ordinal is not None:
            if ordinal in seen_ord and seen_ord[ordinal] != ctitle:
                warnings.append(f"ordinal conflict in TOC at block {i}: chapter {ordinal} titles differ; keeping first")
                # Keep the first mapping, skip this conflicting line
            else:
                seen_ord[ordinal] = ctitle
        idx = len(entries)
        entries.append(
            {
                "chapter_index": idx,
                "title": title,
                "ordinal": ordinal,
                "start_block": -1,
                "end_block": -1,
            }
        )
        last_text = text
        last_item_block = i
        i += 1
    if not entries:
        raise ValueError("No TOC entries parsed")
    return entries, last_item_block, warnings


def _is_body_heading_block(block: dict[str, Any]) -> re.Match[str] | None:
    """Return regex match if this block is a plausible standalone heading.

    Uses enriched fields when available: require 1 line, and short word/char counts.
    """
    text = block.get("text", "")
    lc = block.get("line_count")
    wc = block.get("word_count")
    cc = block.get("char_count")
    if lc is not None and isinstance(lc, int) and lc != 1:
        return None
    if wc is not None and isinstance(wc, int) and wc > MAX_HEADING_WORDS:
        return None
    if cc is not None and isinstance(cc, int) and cc > MAX_HEADING_CHARS:
        return None
    # Exclude likely TOC item lines that have dotted leaders and trailing page numbers
    if re.search(r"\.{2,}\s*\d+\s*$", text):
        return None
    return BODY_HEADING_RE.match(text)


def _looks_like_toc_item_line(text: str) -> bool:
    """Heuristic: line resembles a TOC entry (strict or fallback)."""
    return bool(TOC_ITEM_RE_STRICT.match(text) or TOC_ITEM_RE_FALLBACK.match(text))


def _match_chapters(
    blocks: list[dict[str, Any]], toc_entries: list[dict[str, Any]], start_search: int
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    claimed_heading_indices: set[int] = set()
    # Prevent using two headings that originated from the same source block index
    claimed_heading_src_indices: set[int] = set()
    search_pos = max(start_search, 0)
    # Track minimum allowed start_line to enforce forward progression by original document lines
    min_start_line = -1
    if search_pos > 0 and (search_pos - 1) < len(blocks):
        prev = blocks[search_pos - 1]
        prev_end_line = prev.get("end_line")
        if isinstance(prev_end_line, int):
            min_start_line = prev_end_line
    for entry in toc_entries:
        title = entry["title"]
        ctitle = canon_title(title)
        ordinal = entry.get("ordinal")
        found_idx: int | None = None
        mode = ""
        i = search_pos
        while i < len(blocks):
            blk = blocks[i]
            # Respect line bounds if available
            sl = blk.get("start_line")
            if isinstance(sl, int) and sl <= min_start_line:
                i += 1
                continue
            m = _is_body_heading_block(blk)
            if m:
                # If this heading candidate comes from the same source block index
                # as a previously claimed heading, skip it to avoid ambiguous multi-heading blocks
                src_idx = blk.get("index")
                if isinstance(src_idx, int) and src_idx in claimed_heading_src_indices:
                    i += 1
                    continue
                if i in claimed_heading_indices:
                    raise ValueError(f"Duplicate chapter heading match at block {i}")
                h_title = (m.group("title") or "").strip()
                h_canon = canon_title(h_title)
                h_digits = m.group("digits")
                if h_title and h_title.strip() == title.strip():
                    found_idx = i
                    mode = "exact"
                    break
                if h_title and h_canon == ctitle:
                    found_idx = i
                    mode = "normalized"
                    break
                if ordinal is not None and h_digits and int(h_digits) == ordinal:
                    found_idx = i
                    mode = "ordinal"
                    break
            i += 1
        if found_idx is None:
            raise ValueError(f"Chapter heading not found for TOC entry: '{title}'")
        entry["start_block"] = found_idx
        claimed_heading_indices.add(found_idx)
        src_idx2 = blocks[found_idx].get("index")
        if isinstance(src_idx2, int):
            claimed_heading_src_indices.add(src_idx2)
        # Update min_start_line to enforce forward-only matching by original line number
        next_min_sl = blocks[found_idx].get("start_line")
        if isinstance(next_min_sl, int):
            min_start_line = max(min_start_line, next_min_sl)
        if mode == "normalized":
            warnings.append(f"title normalized match used for TOC entry '{title}' matched at block {found_idx}")
        elif mode == "ordinal":
            warnings.append(
                f"ordinal fallback used for TOC entry '{title}' (chapter {ordinal}) matched at block {found_idx}"
            )
        search_pos = found_idx + 1
    for idx, entry in enumerate(toc_entries):
        if idx < len(toc_entries) - 1:
            entry["end_block"] = toc_entries[idx + 1]["start_block"] - 1
        else:
            entry["end_block"] = len(blocks) - 1
    return toc_entries, warnings


def classify_blocks(jsonl_path: str) -> dict[str, Any]:
    blocks = _load_jsonl_blocks(jsonl_path)
    toc_start = _find_toc_heading(blocks)
    # Find the first body heading to bound TOC parsing window
    first_body_heading_idx = None
    saw_non_heading_after_toc = False
    for i in range(toc_start + 1, len(blocks)):
        b = blocks[i]
        m = _is_body_heading_block(b)
        if m:
            # Only treat as first body heading if we've passed a non-heading
            # separator line (e.g., Preface/Preamble text)
            if saw_non_heading_after_toc:
                first_body_heading_idx = i
                break
            # Otherwise, this is likely still part of the TOC region; continue scanning
        else:
            # Any non-heading line after the TOC indicates we've left the TOC list area
            saw_non_heading_after_toc = True
    toc_entries, toc_end, toc_warnings = _parse_toc_items(blocks, toc_start, first_body_heading_idx)
    start_search = first_body_heading_idx or toc_end + 1
    matched_entries, match_warnings = _match_chapters(blocks, toc_entries, start_search)
    toc_all_warnings = toc_warnings + match_warnings
    claimed = [False] * len(blocks)
    for bi in range(toc_start, toc_end + 1):
        claimed[bi] = True
    chapters_out = []
    for e in matched_entries:
        s, eidx = e["start_block"], e["end_block"]
        for bi in range(s, eidx + 1):
            claimed[bi] = True
        paragraphs = [blocks[bi]["text"] for bi in range(s, eidx + 1)]
        chapters_out.append(
            {
                "chapter_index": e["chapter_index"],
                "title": e["title"],
                "start_block": s,
                "end_block": eidx,
                "paragraphs": paragraphs,
            }
        )
    first_ch_start = matched_entries[0]["start_block"]
    front_span = [-1, -1]
    front_paras: list[str] = []
    front_warn: list[str] = []
    if toc_start > 0:
        unclaimed_pre = [i for i in range(first_ch_start) if not claimed[i]]
        if unclaimed_pre:
            front_span = [unclaimed_pre[0], unclaimed_pre[-1]]
            front_paras = [blocks[i]["text"] for i in unclaimed_pre]
            front_warn = [f"unclaimed blocks: {unclaimed_pre}"]
    last_ch_end = matched_entries[-1]["end_block"]
    back_span = [-1, -1]
    back_paras: list[str] = []
    if last_ch_end < len(blocks) - 1:
        unclaimed_post = [i for i in range(last_ch_end + 1, len(blocks)) if not claimed[i]]
        if unclaimed_post:
            back_span = [unclaimed_post[0], unclaimed_post[-1]]
            back_paras = [blocks[i]["text"] for i in unclaimed_post]
    toc_out = {
        "entries": [
            {
                "chapter_index": e["chapter_index"],
                "title": e["title"],
                "start_block": e["start_block"],
                "end_block": e["end_block"],
            }
            for e in matched_entries
        ],
        "warnings": toc_all_warnings,
        "toc_span_blocks": [toc_start, toc_end],
    }
    chapters_json = {"chapters": chapters_out}
    front_json = {"span_blocks": front_span, "paragraphs": front_paras, "warnings": front_warn}
    back_json = {"span_blocks": back_span, "paragraphs": back_paras, "warnings": []}
    return {
        "toc": toc_out,
        "chapters": chapters_json,
        "front_matter": front_json,
        "back_matter": back_json,
    }
