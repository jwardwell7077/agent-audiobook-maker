from __future__ import annotations

from typing import List

import regex

SENTENCE_SPLIT = regex.compile(r"(?<=[.!?])\s+")
WHITESPACE = regex.compile(r"\s+")


def sentences(text: str) -> List[str]:
    """Split ``text`` into naive sentences using punctuation boundaries."""
    if not text:
        return []
    parts = SENTENCE_SPLIT.split(text.strip())
    results: List[str] = []
    for part in parts:
        normalized = normalize_ws(part)
        if normalized:
            results.append(normalized)
    return results


def window(items: List[str], index: int, k: int = 1) -> str:
    """Return sentence ``index`` with ``k`` sentences of context on either side."""
    if not items:
        return ""
    start = max(index - k, 0)
    end = min(index + k + 1, len(items))
    segment = " ".join(items[start:end])
    return normalize_ws(segment)


def normalize_ws(value: str) -> str:
    """Collapse whitespace in ``value`` and strip leading/trailing spaces."""
    return WHITESPACE.sub(" ", value).strip()
