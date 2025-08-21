"""Structured TOC + chapter parser.

Extracts intro, toc entries, and chapter bodies from raw full-text of a
PDF using regex patterns similar to provided reference script.

Output format (intermediate):
{
  "intro": str,           # may be empty
  "toc": [ {"number": int, "title": str}, ... ],
  "chapters": [ {"number": int, "title": str, "text": str}, ... ]
}

The parser is intentionally conservative; it only returns a result if it
finds at least 2 chapter headings or a TOC with >= 2 entries.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

TOC_HEADER_RE = re.compile(
    r"^\s*Table of Contents\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
# Allow zero or more spaces between 'Chapter' and number to handle extraction
# cases like 'Chapter1:Title' where spacing is lost.
TOC_LINE_RE = re.compile(
    (r"^\s*(?:[•\-*]\s*)?Chapter\s*(\d{1,5})\s*[:\-]?\s*(.+?)" r"\s*(?:\.{2,}\s*\d+)?\s*$"),
    re.IGNORECASE,
)
CH_HDR_RE = re.compile(
    r"^\s*Chapter\s*(\d{1,5})\s*[:\-]?\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_structured_toc(full_text: str, max_chapter: int = 3000) -> dict[str, Any] | None:
    """Return structured book dict or None if confidence too low."""
    text = full_text.replace("\r\n", "\n").replace("\r", "\n")
    toc: list[dict[str, Any]] = []
    intro = ""
    toc_region: tuple[int, int] | None = None

    m_toc = TOC_HEADER_RE.search(text)
    if m_toc:
        start_hdr, end_hdr = m_toc.span()
        substr = text[end_hdr:]
        offset = end_hdr
        nonmatch_streak = 0
        last_match_end = end_hdr
        saw_any = False
        for line in substr.splitlines(keepends=True):
            mo = TOC_LINE_RE.match(line)
            if mo:
                nonmatch_streak = 0
                saw_any = True
                try:
                    num = int(mo.group(1))
                except ValueError:
                    num = -1
                title = mo.group(2).strip()
                if 1 <= num <= max_chapter:
                    toc.append({"number": num, "title": title})
                last_match_end = offset + len(line)
            else:
                nonmatch_streak += 1
                if saw_any:  # first non-match after entries ends region
                    break
            offset += len(line)
        toc_region = (start_hdr, last_match_end if saw_any else end_hdr)
        intro = text[:start_hdr].strip()

    ch_matches: list[tuple[int, int, int, str]] = []
    for mo in CH_HDR_RE.finditer(text):
        s, e = mo.span()
        if toc_region and toc_region[0] <= s < toc_region[1]:  # skip TOC
            continue
        try:
            num = int(mo.group(1))
        except ValueError:
            continue
        if not (1 <= num <= max_chapter):
            continue
        title = mo.group(2).strip()
        # Remove trailing dotted leader or page number artifacts
        title = re.sub(r"(?:\.{2,}|\s)+\d+$", "", title).strip()
        ch_matches.append((s, e, num, title))

    ch_matches.sort(key=lambda t: t[0])

    if not m_toc and ch_matches and ch_matches[0][0] > 0:
        intro = text[: ch_matches[0][0]].strip()

    chapters: list[dict[str, Any]] = []
    for i, (s, e, num, title) in enumerate(ch_matches):
        next_start = ch_matches[i + 1][0] if i + 1 < len(ch_matches) else len(text)
        body = text[e:next_start].strip()
        chapters.append({"number": num, "title": title, "text": body})

    # Confidence checks
    if len(chapters) < 2 and len(toc) < 2:  # too weak
        return None

    toc_sorted = sorted(toc, key=lambda x: x["number"]) if toc else []
    # Deduplicate TOC entries by chapter number while preserving first title.
    # Duplicate numbers occasionally arise from malformed extraction where the
    # same line is emitted twice. Keeping only the first occurrence makes
    # downstream consistency checks simpler.
    deduped: list[dict[str, Any]] = []
    seen_nums: set[int] = set()
    for entry in toc_sorted:
        num = entry["number"]
        if num in seen_nums:
            continue
        seen_nums.add(num)
        deduped.append(entry)
    if os.environ.get("INGEST_DEBUG_STRUCTURE"):
        dup_count = len(toc_sorted) - len(deduped)
        logging.getLogger(__name__).info(
            "structured_toc debug toc=%d (dedup -%d) heads=%d intro_len=%d",
            len(deduped),
            dup_count,
            len(chapters),
            len(intro),
        )
    return {"intro": intro, "toc": deduped, "chapters": chapters}
