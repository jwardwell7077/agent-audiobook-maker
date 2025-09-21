"""Text normalization utilities for voice engines.

This module centralizes light, safe normalizations used across engines
so cache keys and runtime behavior stay consistent.
"""

from __future__ import annotations

import re

__all__ = [
    "normalize_quotes_and_dashes",
    "sanitize_angle_brackets",
]


def normalize_quotes_and_dashes(s: str) -> str:
    """Normalize curly quotes and long dashes to ASCII equivalents.

    This mirrors the mapping historically used in the Parler engine.
    """

    repl = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


_TAG = re.compile(r"</?([A-Za-z][A-Za-z0-9_-]*)(?:\s[^>]*)?>")


def sanitize_angle_brackets(text: str, role: str | None) -> str:
    """Make `<...>` safe for TTS. Role-aware.

    Behavior:
    - ai/system roles: strip XML-like tags but keep inner text.
    - math-like spaced operators: `<` and `>` become words when spaced on both sides.
    - fallback: replace any remaining `<` or `>` with `[` and `]`.
    Also collapses whitespace.
    """

    s = text

    # 1) Strip XML-ish tags for AI/system roles
    if (role or "").lower() in ("ai-system", "ai", "system"):
        s = _TAG.sub("", s)

    # 2) Spaced math operators to words: " a < b " / " a > b "
    s = re.sub(r"(?<=\s)<(?=\s)", " less than ", s)
    s = re.sub(r"(?<=\s)>(?=\s)", " greater than ", s)

    # 3) Fallback: bracketize any remaining angle brackets
    s = s.replace("<", "[").replace(">", "]")

    # 4) Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s
