"""Build and merge speaker rosters for chapters.

This module provides a `RosterBuilder` class that combines lightweight
heuristics with optional spaCy NER and rapidfuzz fuzzy matching to extract
character names from chapter text. The resulting mapping of canonical names to
aliases can be merged across chapters to form a book-level roster.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module, util
from typing import Any

# Optional deps; handled gracefully if missing.
spacy: Any
rapidfuzz: Any
fuzz: Any
spacy_spec = util.find_spec("spacy")
if spacy_spec is not None:  # pragma: no cover - optional import
    spacy = import_module("spacy")
    _HAS_SPACY = True
else:  # pragma: no cover - import guard
    spacy = None
    _HAS_SPACY = False

rf_spec = util.find_spec("rapidfuzz")
if rf_spec is not None:  # pragma: no cover - optional import
    rapidfuzz = import_module("rapidfuzz")
    fuzz = rapidfuzz.fuzz
    _HAS_RAPIDFUZZ = True
else:  # pragma: no cover - import guard
    rapidfuzz = None
    fuzz = None
    _HAS_RAPIDFUZZ = False


@dataclass
class RosterConfig:
    """Configuration for :class:`RosterBuilder` behavior.

    Attributes:
        use_spacy: Whether to use spaCy NER if available.
        fuzzy_threshold: Similarity threshold for alias merging (0–100).
        person_titles: Known person titles to strip when forming a canonical name.
        split_full_names: Whether to add first/last (and middle) tokens as aliases.
        max_alias_len: Max characters to keep per alias (avoid noisy mega-strings).
    """

    use_spacy: bool = True
    fuzzy_threshold: int = 90
    person_titles: tuple[str, ...] = (
        "mr",
        "mrs",
        "ms",
        "miss",
        "dr",
        "prof",
        "sir",
        "lady",
        "lord",
        "capt",
        "captain",
        "lt",
        "sgt",
        "sergeant",
        "gen",
        "colonel",
    )
    split_full_names: bool = True
    max_alias_len: int = 64


class RosterBuilder:
    """Build chapter- and book-level speaker rosters from raw text."""

    # High-signal regex heuristics.
    RE_ANGLE_USER = re.compile(r"<\s*User\s*:\s*([^>]+)>\s*$", re.IGNORECASE)
    RE_VOCATIVE = re.compile(r'"[^"\n]*,\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})[!?]"')
    RE_TITLE_NAME = re.compile(
        r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|Sir|Lady|Lord|Capt|Captain|Lt|Sgt|Sergeant|Gen|Colonel)\.??\s+([A-Z][a-z]+)\b"
    )

    def __init__(self, config: RosterConfig | None = None, nlp: Any | None = None) -> None:
        """Initialize the :class:`RosterBuilder`.

        Args:
            config: Optional configuration overrides.
            nlp: Optional preloaded spaCy pipeline; if ``None`` and spaCy is
                available, a lightweight pipeline will be loaded on first use.
        """

        self.cfg = config or RosterConfig()
        self._nlp = nlp

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_chapter_roster(self, text: str) -> dict[str, list[str]]:
        """Return a chapter roster mapping canonical name → aliases.

        The method combines spaCy PERSON entities (if enabled) with several
        deterministic heuristics (angle-tag user lines, vocatives, and
        title+name patterns).

        Args:
            text: Chapter text.

        Returns:
            Dictionary mapping canonical names to sorted lists of aliases.
        """

        name_counts: Counter[str] = Counter()

        # 1) Heuristics (high signal)
        for m in self.RE_ANGLE_USER.finditer(text):
            name_counts[self._clean_alias(m.group(1))] += 3  # weighted
        for m in self.RE_VOCATIVE.finditer(text):
            name_counts[self._clean_alias(m.group(1))] += 1
        for m in self.RE_TITLE_NAME.finditer(text):
            name_counts[self._clean_alias(m.group(1))] += 1

        # 2) spaCy NER
        if self.cfg.use_spacy and _HAS_SPACY:
            doc = self._get_nlp()(text)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    name_counts[self._clean_alias(ent.text)] += 1

        # 3) Canonicalize + alias expansion
        raw_aliases = {a for a in name_counts if a}
        preliminary = self._canonicalize_group(raw_aliases)
        roster = {canon: self._expand_aliases(canon, alist) for canon, alist in preliminary.items()}

        # 4) Fuzzy merge within the chapter
        roster = self._fuzzy_merge(roster, self.cfg.fuzzy_threshold)

        return {k: sorted(v) for k, v in roster.items()}

    def merge_book_roster(
        self, book_roster: dict[str, list[str]], chapter_roster: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Merge a chapter roster into a book roster with optional fuzzy aliasing.

        Args:
            book_roster: Existing book-level mapping.
            chapter_roster: New chapter-level mapping.

        Returns:
            Updated book-level mapping with merged aliases.
        """

        out: dict[str, set[str]] = {k: set(v) for k, v in (book_roster or {}).items()}

        for canon, aliases in chapter_roster.items():
            placed = False
            for k, vals in out.items():
                if canon == k or canon in vals or any(a in vals for a in aliases):
                    vals.update(aliases + [canon])
                    placed = True
                    break
            if placed:
                continue

            if _HAS_RAPIDFUZZ:
                best_k = None
                best_score = -1
                for k in out.keys():
                    score = fuzz.ratio(canon.lower(), k.lower())
                    if score > best_score:
                        best_k, best_score = k, score
                if best_k is not None and best_score >= self.cfg.fuzzy_threshold:
                    out[best_k].update(aliases + [canon])
                    continue

            out[canon] = set(aliases + [canon])

        return {k: sorted(v) for k, v in out.items()}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _canonicalize_group(self, aliases: set[str]) -> dict[str, list[str]]:
        """Group aliases under a canonical key by simple rules.

        Rules:
            * Strip known titles from the left ("Sergeant Griff" → "Griff").
            * Group by the last token; choose the longest alias containing it
              as canonical.
        """

        by_last: dict[str, set[str]] = defaultdict(set)
        for a in aliases:
            base = self._strip_title(a)
            toks = base.split()
            last = toks[-1] if toks else base
            by_last[last].add(base)

        result: dict[str, list[str]] = {}
        for group in by_last.values():
            canon = max(sorted(group), key=len)
            result[canon] = sorted(group)
        return result

    def _expand_aliases(self, canonical: str, aliases: Sequence[str]) -> set[str]:
        """Add useful subparts of names as aliases (first, last, full)."""

        out: set[str] = set()
        for a in aliases:
            a_clean = self._clean_alias(a)
            if not a_clean:
                continue
            out.add(a_clean)
            toks = a_clean.split()
            if self.cfg.split_full_names and 1 < len(toks) <= 3:
                out.add(toks[0])
                out.add(toks[-1])
        out.add(self._clean_alias(canonical))
        return {x for x in out if 0 < len(x) <= self.cfg.max_alias_len}

    def _fuzzy_merge(self, roster: dict[str, set[str]], threshold: int) -> dict[str, set[str]]:
        """Merge near-duplicate canonicals within a roster using fuzzy matching."""

        if not _HAS_RAPIDFUZZ or len(roster) < 2:
            return roster

        keys = list(roster.keys())
        parent: dict[str, str] = {k: k for k in keys}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                score = fuzz.ratio(a.lower(), b.lower())
                if score >= threshold:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[rb] = ra

        merged: dict[str, set[str]] = defaultdict(set)
        for k, aliases in roster.items():
            root = find(k)
            merged[root].update(aliases)
            merged[root].add(k)
        return merged

    def _strip_title(self, name: str) -> str:
        """Strip a leading person title if present."""

        if not name:
            return name
        toks = name.strip().split()
        if toks and toks[0].rstrip(".").lower() in self.cfg.person_titles:
            toks = toks[1:]
        return " ".join(toks)

    @staticmethod
    def _clean_alias(name: str) -> str:
        """Normalize whitespace and strip surrounding punctuation for an alias."""

        if not name:
            return name
        s = " ".join(name.strip().split())
        return s.strip(" \t\r\n\"'.,:;!?-–—")

    def _get_nlp(self) -> Any:  # pragma: no cover - simple getter
        """Return a spaCy pipeline, creating one if needed."""

        if self._nlp is not None:
            return self._nlp
        if not _HAS_SPACY:
            raise RuntimeError("spaCy is not installed but use_spacy=True.")
        try:
            self._nlp = spacy.load("en_core_web_trf")
        except Exception:
            self._nlp = spacy.load("en_core_web_sm")
        return self._nlp


# ---------------------------------------------------------------------------
# Backwards-compatible functional wrappers
# ---------------------------------------------------------------------------


def build_chapter_roster(text: str, nlp: Any | None = None) -> dict[str, list[str]]:
    """Functional wrapper for building a chapter roster.

    Args:
        text: Chapter text.
        nlp: Optional spaCy pipeline to reuse.

    Returns:
        Dictionary mapping canonical speaker names to alias lists.
    """

    rb = RosterBuilder(nlp=nlp)
    return rb.build_chapter_roster(text)


def merge_book_roster(book: dict[str, list[str]], chap: dict[str, list[str]]) -> dict[str, list[str]]:
    """Functional wrapper for merging rosters (compatibility helper)."""

    rb = RosterBuilder()
    return rb.merge_book_roster(book, chap)

