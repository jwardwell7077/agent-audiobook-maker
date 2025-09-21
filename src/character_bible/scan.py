from __future__ import annotations

from typing import Iterable, List

import regex

from .schema import EvidenceSnippet
from .textutils import normalize_ws, sentences, window


def _build_pattern(name: str, aliases: Iterable[str]) -> regex.Pattern[str] | None:
    tokens = []
    seen = set()
    for candidate in [name, *aliases]:
        if not candidate:
            continue
        normalized = candidate.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(regex.escape(normalized))

    if not tokens:
        return None

    pattern = rf"(?i)(?<!\w)(?:{'|'.join(tokens)})(?!\w)"
    return regex.compile(pattern)


def find_mentions(
    chapters: Iterable[dict[str, str]],
    name: str,
    aliases: List[str] | None = None,
    max_hits: int = 10,
    sent_window: int = 1,
) -> List[EvidenceSnippet]:
    """Return contextual evidence snippets for mentions of ``name`` or ``aliases``."""
    if aliases is None:
        aliases = []

    pattern = _build_pattern(name, aliases)
    if pattern is None:
        return []

    snippets: List[EvidenceSnippet] = []
    seen_text: set[str] = set()

    for chapter in chapters:
        chapter_title = chapter.get("title")
        chapter_id = chapter.get("id") or chapter_title
        text = str(chapter.get("text", ""))
        chapter_sentences = sentences(text)
        for idx, sentence in enumerate(chapter_sentences):
            if not pattern.search(sentence):
                continue
            excerpt = window(chapter_sentences, idx, k=sent_window)
            normalized = normalize_ws(excerpt)
            if not normalized or normalized in seen_text:
                continue
            seen_text.add(normalized)
            snippets.append(
                EvidenceSnippet(
                    chapter=chapter_title,
                    location=f"{chapter_id}: sentence {idx + 1}",
                    text=normalized,
                )
            )
            if len(snippets) >= max_hits:
                return snippets

    return snippets


def count_mentions(chapters: Iterable[dict[str, str]], name: str, aliases: List[str] | None = None) -> int:
    """Count total mentions of ``name`` and ``aliases`` across ``chapters``."""
    if aliases is None:
        aliases = []

    pattern = _build_pattern(name, aliases)
    if pattern is None:
        return 0

    total = 0
    for chapter in chapters:
        text = str(chapter.get("text", ""))
        total += len(pattern.findall(text))
    return total
