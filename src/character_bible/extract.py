from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .scan import count_mentions, find_mentions
from .schema import CharacterSeed, EvidenceSnippet


def parse_candidate(raw: str) -> Tuple[str, List[str]]:
    """Parse a raw candidate line into a canonical name and aliases."""
    if raw is None:
        raise ValueError("Candidate name cannot be None")

    stripped = raw.strip()
    if not stripped:
        raise ValueError("Candidate name cannot be empty")

    parts = [part.strip() for part in stripped.split("|") if part.strip()]
    if not parts:
        raise ValueError("Candidate name cannot be empty")

    name = parts[0]
    aliases = parts[1:]

    tokens = name.split()
    alias_keys = {alias.lower() for alias in aliases}
    if len(tokens) > 1:
        primary = tokens[0]
        if primary.lower() not in alias_keys:
            aliases.append(primary)
    return name, aliases


def seed_from_counts(chapters: Sequence[dict[str, str]], candidates: Iterable[str]) -> List[CharacterSeed]:
    """Create ``CharacterSeed`` objects for ``candidates`` with mention counts."""
    ranked: List[tuple[CharacterSeed, int]] = []
    for candidate in candidates:
        try:
            name, aliases = parse_candidate(candidate)
        except ValueError:
            continue
        seed = CharacterSeed(name=name, aliases=aliases)
        count = count_mentions(chapters, name, aliases)
        ranked.append((seed, count))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return [seed for seed, _ in ranked]


def first_mentions(
    chapters: Sequence[dict[str, str]],
    seed: CharacterSeed,
    max_hits: int = 5,
    sent_window: int = 1,
) -> List[EvidenceSnippet]:
    """Collect the earliest contextual evidence for ``seed`` mentions."""
    return find_mentions(chapters, seed.name, seed.aliases, max_hits=max_hits, sent_window=sent_window)


__all__ = ["parse_candidate", "seed_from_counts", "first_mentions"]
