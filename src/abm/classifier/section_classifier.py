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
_TOC_ITEM_RE = re.compile(
    r"^\s*(?:[•\-*]\s*)?(?:chapter\s+\d+|prologue|epilogue)\s*[:.\-]?\s*(?P<title>.+?)\s*$",
    re.IGNORECASE,
)
_CHAPTER_HEADING_RE_TMPL = r"^\s*(?:chapter\s+{num}|{alt})\s*[:.\-]?\s*(?P<title>.+)?$"


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
    look = blocks[idx + 1: idx + 6]
    score = 0
    collected_lines: list[str] = []
    for b in look:
        for ln in b.splitlines():
            if _TOC_ITEM_RE.match(ln.strip()):
                score += 1
                collected_lines.append(ln.strip())
    if score < 2:
        raise ValueError("TOC heading found but no TOC items ahead")

    # Parse items from heading block forward until first body chapter heading is encountered
    items: list[dict[str, Any]] = []
    toc_end = idx
    for j in range(idx, min(len(blocks), idx + 1000)):
        toc_end = j
        lines = [ln.strip() for ln in blocks[j].splitlines() if ln.strip()]
        any_item = False
        for ln in lines:
            m = _TOC_ITEM_RE.match(ln)
            if not m:
                continue
            any_item = True
            title = m.group("title").strip()
            # Extract ordinal if present
            num = None
            mnum = re.search(r"chapter\s+(\d+)", ln, flags=re.IGNORECASE)
            if mnum:
                num = int(mnum.group(1))
            items.append({"ordinal": num, "title": title})
        if not any_item and j > idx:
            # Stop when a non-TOC block appears after initial items
            break
    toc_end = max(idx, toc_end)
    if not items:
        raise ValueError("No TOC entries parsed")
    return TOCDetection(toc_start=idx, toc_end=toc_end, items=items)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _find_chapter_headings(blocks: list[str], toc: TOCDetection) -> list[tuple[int, str]]:
    """Return list of (block_index, title) in chapter order based on TOC.

    Match primarily by title; fallback to ordinal. Accept prologue/epilogue.
    Error if a TOC entry cannot be located in body.
    """

    start_search = toc.toc_end + 1
    found: list[tuple[int, str]] = []
    used_indices: set[int] = set()

    for item in toc.items:
        title = item["title"]
        ordinal = item.get("ordinal")
        title_norm = _normalize(title)

        match_idx = None

        # 1) Try to match by title within a block heading
        for i in range(start_search, len(blocks)):
            blk = blocks[i]
            lines = blk.splitlines()
            # Count potential headings in block
            cand_lines = [
                ln for ln in lines if re.match(r"^\s*(chapter\s+\d+|prologue|epilogue)\b", ln, flags=re.IGNORECASE)
            ]
            if len(cand_lines) > 1:
                raise ValueError(f"Multiple chapter headings detected in one block at {i}")
            for ln in lines:
                # heading start anchored
                if re.match(r"^\s*(chapter\s+\d+|prologue|epilogue)\b", ln, flags=re.IGNORECASE):
                    # Compare titles loosely
                    after = re.sub(r"^\s*(?:chapter\s+\d+|prologue|epilogue)\s*[:.\-]?\s*", "", ln, flags=re.IGNORECASE)
                    if _normalize(after).startswith(title_norm[: max(3, len(title_norm) // 2)]):
                        match_idx = i
                        break
            if match_idx is not None:
                break

        # 2) Fallback: match by ordinal only
        if match_idx is None and ordinal is not None:
            rx = re.compile(rf"^\s*chapter\s+{ordinal}\b", flags=re.IGNORECASE)
            for i in range(start_search, len(blocks)):
                if rx.search(blocks[i]):
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
                "chapter_index": ci,  # 0-based
                "chapter_number": ci + 1,  # 1-based
                "title": title,
                "start_block": start_idx,
                "end_block": end_idx,
                "paragraphs": blocks[start_idx: end_idx + 1],
            }
        )

    # Build TOC entries based on chapters
    toc_entries = [
        {
            "chapter_index": ch["chapter_index"],  # 0-based
            "chapter_number": ch["chapter_number"],  # 1-based
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
