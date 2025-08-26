"""Block-based Section Classifier (paragraph-first).

Inputs: a list of text blocks (paragraphs) split on blank-line boundaries.
Outputs: four JSON-friendly dicts for toc, chapters, front_matter, back_matter.

Key rules:
- Split on blank-line boundaries; preserve inner newlines; drop whitespace-only blocks.
- Zero-based block indices everywhere; spans are inclusive [start_block, end_block].
- Detect a TOC heading anchored at line start (allow leading whitespace), then
    look ahead up to 5 blocks for TOC-like chapter list lines. On failure → raise.
- Parse TOC entries (titles), then match chapter headings in the body primarily by
    title; fallback to ordinal only. Accept Prologue/Epilogue as chapters.
- Each chapter is a contiguous inclusive block range from its heading to the block
    before the next heading. Heading block is paragraph index 0 of the chapter.
- Multiple chapter headings in one block → raise. TOC entry not found in body → raise.
- Front matter: all unclaimed blocks before first chapter, excluding TOC blocks.
- Back matter: all unclaimed blocks after last chapter.
- Include warnings listing unclaimed block indices.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TOC_HEADING_RE = re.compile(r"^\s*(table of contents|contents)\b", re.IGNORECASE)
# TOC item line forms:
# - Chapter 1: Title
# - 1. Title
# - I. Title
# - Prologue / Epilogue [: Title]
_TOC_ITEM_RE = re.compile(
    r"^\s*(?:[•\-*]\s*)?"  # optional bullet
    r"(?:"
    r"(?:chapter\s+(?P<num>\d+))|"  # Chapter N
    r"(?P<roman>[ivxlcdm]+)\.?|"  # Roman numerals (I, II, ...)
    r"(?P<digit>\d+)\.?|"  # Decimal index (1, 2, ...)
    r"(?P<pe>prologue|epilogue)"  # Prologue/Epilogue
    r")\s*"
    # Optional separator: any single character with whitespace around; OR no separator, just spaces before title.
    # Entire title segment optional to allow bare 'Prologue'/'Epilogue' entries.
    r"(?:\s*(?:.\s+)?(?P<title>.+))?\s*$",
    re.IGNORECASE,
)

# Chapter heading line detection within body must also support the same forms
_HEADING_PREFIX_RE = re.compile(
    r"^\s*(?:chapter\s+\d+|[ivxlcdm]+\.?|\d+\.?|prologue|epilogue)\b",
    re.IGNORECASE,
)


def _split_blocks(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text)
    return [p for p in parts if p and p.strip()]


@dataclass
class TOCDetection:
    toc_start: int
    toc_end: int  # inclusive end block index
    items: list[dict[str, Any]]  # [{ordinal (int|None), title: str}]


def _detect_and_parse_toc(blocks: list[str]) -> TOCDetection:
    # Find heading
    idx = None
    for i, blk in enumerate(blocks):
        for line in blk.splitlines():
            if _TOC_HEADING_RE.match(line):
                idx = i
                break
        if idx is not None:
            break
    if idx is None:
        raise ValueError("TOC heading not found")

    # Look ahead up to 5 blocks for TOC-like lines
    look = blocks[idx + 1 : idx + 6]
    score = 0
    any_idx_rel: list[int] = []
    for rel_i, b in enumerate(look, start=1):
        for ln in b.splitlines():
            if _TOC_ITEM_RE.match(ln.strip()):
                score += 1
                any_idx_rel.append(rel_i)
    if score < 2:
        raise ValueError("TOC heading found but no TOC items ahead")

    # Parse items strictly within the lookahead window to avoid swallowing body headings
    items: list[dict[str, Any]] = []
    toc_end = idx
    for j in range(idx + 1, min(len(blocks), idx + 6)):
        lines = [ln.strip() for ln in blocks[j].splitlines() if ln.strip()]
        any_item = False
        for ln in lines:
            m = _TOC_ITEM_RE.match(ln)
            if not m:
                continue
            any_item = True
            # Title resolution: if explicit title exists, use it; for Prologue/Epilogue without title, use the label
            title = m.group("title")
            pe = m.group("pe") if m.groupdict().get("pe") else None
            if title is None:
                title = pe if pe else ""
            title = title.strip()
            # Extract ordinal if present (digit or roman or chapter N)
            num = None
            if m.groupdict().get("num"):
                num = int(m.group("num"))
            elif m.groupdict().get("digit"):
                num = int(m.group("digit"))
            elif m.groupdict().get("roman"):
                num = _roman_to_int(m.group("roman"))
            items.append({"ordinal": num, "title": _title_core(title)})
        if any_item:
            toc_end = j
    if toc_end == idx and any_idx_rel:
        toc_end = idx + max(any_idx_rel)
    if not items:
        raise ValueError("No TOC entries parsed")
    return TOCDetection(toc_start=idx, toc_end=toc_end, items=items)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _title_core(s: str) -> str:
    """Normalize a title for matching: remove dot leaders, trailing page numbers, and punctuation.

    Example: 'Chapter 3: Miltary School .......... 12' -> 'miltary school'
    """
    s = s.strip()
    # Remove dot leaders and similar fillers
    s = re.sub(r"[.·•]{2,}", " ", s)
    # Drop trailing page numbers
    s = re.sub(r"[ .·•]*\d+\s*$", "", s)
    # Remove non-word punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    return _normalize(s)


def _roman_to_int(s: str) -> int | None:
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    s = s.lower().strip()
    if not s:
        return None
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals.get(ch)
        if v is None:
            return None
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def _int_to_roman(num: int) -> str:
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
    res = []
    n = num
    for v, sym in vals:
        while n >= v:
            res.append(sym)
            n -= v
    return "".join(res)


def _levenshtein(a: str, b: str, max_dist: int) -> int:
    """Compute Levenshtein distance with an optional early exit.

    Simple O(len(a)*len(b)) DP with early stop when row minimum exceeds max_dist.
    """
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    # Ensure a is shorter
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        min_row = curr[0]
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,  # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution
            )
            if curr[j] < min_row:
                min_row = curr[j]
        if min_row > max_dist:
            return max_dist + 1
        prev = curr
    return prev[-1]


def _looks_like_title(s: str) -> bool:
    """Heuristic: short-ish, title-cased or uppercase, likely a heading.

    This helps match chapter headings that omit 'Chapter N' prefixes.
    """
    s = s.strip()
    if not s:
        return False
    if len(s) <= 6:  # too short to be reliable
        return False
    if len(s) > 120:
        return False
    if s.isupper():
        return True
    words = [w for w in re.split(r"\s+", s) if w]
    if not words:
        return False
    caps = sum(1 for w in words if w[0:1].isupper())
    return caps / max(1, len(words)) >= 0.6


def _find_chapter_headings(blocks: list[str], toc: TOCDetection) -> list[tuple[int, str]]:
    """Return list of (block_index, title) in chapter order based on TOC.

    Multi-pass mapping per TOC item to ensure determinism and resilience:
    1) Exact title match (normalized equality) on detected heading lines.
    2) Ordinal match (decimal or Roman) when title not found.
    3) Relaxed match (prefix/fuzzy) as a last resort.

    Accept Prologue/Epilogue as headings. Error if a TOC entry cannot be located.
    """

    start_search = toc.toc_end + 1
    found: list[tuple[int, str]] = []
    used_indices: set[int] = set()

    # Helpers
    heading_prefix_only = re.compile(
        r"^\s*(?:chapter\s+(?P<num>\d+)|(?P<roman>[ivxlcdm]+)\.?|(?P<digit>\d+)\.?|(?P<pe>prologue|epilogue))\b",
        re.IGNORECASE,
    )

    def extract_heading_info(blk: str) -> tuple[bool, str | None, int | None, int]:
        """Return (has_heading, normalized_title, ordinal, heading_lines_count).

        normalized_title is after stripping heading prefix and optional single-char separator.
        ordinal is int if present else None.
        heading_lines_count counts lines in block that look like prefixed headings.
        """
        lines = [ln for ln in blk.splitlines() if ln.strip()]
        prefixed = [ln for ln in lines if _HEADING_PREFIX_RE.match(ln)]
        count = len(prefixed)
        if count == 0:
            return False, None, None, 0
        if count > 1:
            raise ValueError("Multiple chapter headings detected in one block")
        ln = prefixed[0]
        # Ordinal
        m = heading_prefix_only.match(ln)
        ord_val: int | None = None
        if m:
            if m.group("num"):
                ord_val = int(m.group("num"))
            elif m.group("digit"):
                ord_val = int(m.group("digit"))
            elif m.group("roman"):
                ord_val = _roman_to_int(m.group("roman"))
        # Title after prefix
        after = re.sub(
            r"^\s*(?:chapter\s+\d+|[ivxlcdm]+\.?|\d+\.?|prologue|epilogue)(?:\s+.\s+)?\s*",
            "",
            ln,
            flags=re.IGNORECASE,
        )
        norm_title = _title_core(after)
        return True, norm_title, ord_val, 1

    for item in toc.items:
        title = item["title"]
        ordinal = item.get("ordinal")
        title_norm = _title_core(title)

        match_idx: int | None = None

        # Pass 1: exact normalized title match
        for i in range(start_search, len(blocks)):
            has_head, norm_title, ord_in_blk, count = extract_heading_info(blocks[i])
            if not has_head:
                continue
            if i in used_indices:
                continue
            if norm_title == title_norm and norm_title:
                match_idx = i
                break

        # Pass 2: ordinal match
        if match_idx is None and ordinal is not None:
            for i in range(start_search, len(blocks)):
                has_head, norm_title, ord_in_blk, count = extract_heading_info(blocks[i])
                if not has_head:
                    continue
                if i in used_indices:
                    continue
                if ord_in_blk is not None and ord_in_blk == ordinal:
                    match_idx = i
                    break

        # Pass 3: relaxed match (prefix/fuzzy)
        if match_idx is None:
            for i in range(start_search, len(blocks)):
                has_head, norm_title, ord_in_blk, count = extract_heading_info(blocks[i])
                if not has_head:
                    continue
                if i in used_indices:
                    continue
                if not norm_title:
                    continue
                if norm_title.startswith(title_norm[: max(3, len(title_norm) // 2)]):
                    match_idx = i
                    break
                max_dist = max(1, min(3, len(title_norm) // 10))
                if _levenshtein(norm_title, title_norm, max_dist) <= max_dist:
                    match_idx = i
                    break

        if match_idx is None:
            raise ValueError(f"Chapter heading not found for TOC entry: '{title}'")
        if match_idx in used_indices:
            raise ValueError(f"Duplicate chapter heading match at block {match_idx}")
        used_indices.add(match_idx)
        found.append((match_idx, title))
        start_search = match_idx + 1

    return found


def classify_sections(inputs: dict[str, Any]) -> dict[str, Any]:
    """Classify sections from blocks and return toc/chapters/front/back artifacts.

    inputs = {"blocks": list[str]}.
    """

    blocks = inputs.get("blocks")
    if blocks is None:
        raise ValueError("missing 'blocks' in inputs")
    if not isinstance(blocks, list) or not all(isinstance(b, str) for b in blocks):
        raise ValueError("'blocks' must be list[str]")

    # Detect and parse TOC
    toc_det = _detect_and_parse_toc(blocks)

    # Find chapter headings according to TOC
    headings = _find_chapter_headings(blocks, toc_det)

    # Build chapter spans
    chapters: list[dict[str, Any]] = []
    claimed = [False] * len(blocks)
    # Claim TOC blocks
    for i in range(toc_det.toc_start, toc_det.toc_end + 1):
        claimed[i] = True

    heading_indices = [idx for idx, _ in headings]
    for ci, (start_idx, title) in enumerate(headings):
        if ci < len(headings) - 1:
            end_idx = heading_indices[ci + 1] - 1
        else:
            end_idx = len(blocks) - 1
        # Claim range
        for i in range(start_idx, end_idx + 1):
            if claimed[i]:
                # shouldn't overlap toc or prior chapters
                pass
            claimed[i] = True
        chapters.append(
            {
                "chapter_index": ci,
                "title": title,
                "start_block": start_idx,
                "end_block": end_idx,
                "paragraphs": blocks[start_idx : end_idx + 1],
            }
        )

    # Build TOC entries based on chapters
    toc_entries = [
        {
            "chapter_index": ch["chapter_index"],
            "title": ch["title"],
            "start_block": ch["start_block"],
            "end_block": ch["end_block"],
        }
        for ch in chapters
    ]

    # Front matter
    first_ch_start = chapters[0]["start_block"] if chapters else 0
    front_indices = [i for i in range(first_ch_start) if not (toc_det.toc_start <= i <= toc_det.toc_end)]
    front_span = [front_indices[0], front_indices[-1]] if front_indices else [-1, -1]
    front_paragraphs = [blocks[i] for i in front_indices]

    # Back matter
    last_ch_end = chapters[-1]["end_block"] if chapters else -1
    back_indices = list(range(last_ch_end + 1, len(blocks))) if last_ch_end + 1 < len(blocks) else []
    back_span = [back_indices[0], back_indices[-1]] if back_indices else [-1, -1]
    back_paragraphs = [blocks[i] for i in back_indices]

    # Unclaimed warnings
    unclaimed = [i for i, c in enumerate(claimed) if not c]

    toc = {"entries": toc_entries}
    chapters_out = {"chapters": chapters}
    front = {
        "span_blocks": front_span,
        "paragraphs": front_paragraphs,
        "warnings": ([f"unclaimed blocks: {unclaimed}"] if unclaimed else []),
    }
    back = {"span_blocks": back_span, "paragraphs": back_paragraphs, "warnings": ([])}

    return {
        "toc": toc,
        "chapters": chapters_out,
        "front_matter": front,
        "back_matter": back,
    }
