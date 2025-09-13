"""Text normalization and safe chunking for TTS."""

from __future__ import annotations

import re

_SMALL = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    100: "one hundred",
    1000: "one thousand",
}
_TENS = {
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}

_ABBR = re.compile(
    r"(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\."
)
_SENT_BOUNDARY = re.compile(
    r"""
    (?<=[.!?…])
    ["'\)\]\u2019\u201D\u2014]*\s+
    (?=[A-Z"'\u201C\u2018])
    """,
    re.VERBOSE,
)


class TextNormalizer:
    """Normalize story/game text to be TTS-friendly.

    Methods here avoid engine dependencies and can be unit-tested in isolation.
    """

    _spaces = re.compile(r"[ \t]+")
    _linebreaks = re.compile(r"\s*\n\s*")
    _angle_stat = re.compile(r"<\s*([A-Za-z]+)\s*([0-9]+)\s*/\s*([0-9]+)\s*>")
    _exp = re.compile(r"\b(\d+)\s*exp\b", re.IGNORECASE)
    _angle_strip = re.compile(r"[<>]")

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize quotes, whitespace, “UI” tokens like <HP 10/10>, and EXP.

        The goal is to produce clear, pronounceable text for TTS engines while
        remaining semantically faithful.

        Args:
            text: Raw text (may include angle-bracket tags, curly quotes, etc.).

        Returns:
            Normalized text, safe for speech synthesis.
        """
        s = (
            text.replace("…", "...")
            .replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )
        s = TextNormalizer._linebreaks.sub(" ", s)
        s = TextNormalizer._spaces.sub(" ", s).strip()

        # <HP 10/10> -> "HP ten out of ten"
        def _stat_sub(m: re.Match[str]) -> str:
            label, a, b = m.group(1), int(m.group(2)), int(m.group(3))
            return f"{label.upper()} {TextNormalizer._num_to_words(a)} out of {TextNormalizer._num_to_words(b)}"

        s = TextNormalizer._angle_stat.sub(_stat_sub, s)

        # 5 exp -> five experience
        def _exp_sub(m: re.Match[str]) -> str:
            n = int(m.group(1))
            return f"{TextNormalizer._num_to_words(n)} experience"

        s = TextNormalizer._exp.sub(_exp_sub, s)

        # Strip remaining angle brackets like <Skills>
        s = TextNormalizer._angle_strip.sub("", s)
        return s

    @staticmethod
    def version() -> str:
        """Return a version string for cache keying."""

        return "1"

    @staticmethod
    def _num_to_words(n: int) -> str:
        """Convert some small integers to words, otherwise return digits.

        Supports 0..20, tens multiples up to 90, and 100/1000.
        """
        if n in _SMALL:
            return _SMALL[n]
        if n in _TENS:
            return _TENS[n]
        return str(n)


class Chunker:
    """Split text into chunks within engine-friendly limits."""

    @staticmethod
    def split(text: str, *, engine: str, max_chars: int | None = None) -> list[str]:
        """Split normalized text into chunks, preferring sentence boundaries.

        Args:
            text: Normalized input text.
            engine: Engine name to choose defaults (e.g., 'piper', 'xtts').
            max_chars: Hard character cap per chunk. Falls back to engine defaults.

        Returns:
            A list of non-empty chunks, each <= max_chars.
        """
        defaults = {"piper": 700, "xtts": 500}
        cap = int(max_chars or defaults.get(engine, 600))

        # First pass: conservative sentence split, keeping "..." intact.
        parts = _SENT_BOUNDARY.split(text.strip())
        parts = [p.strip() for p in parts if p.strip()]

        # Merge pieces that were split after abbreviations
        merged: list[str] = []
        for p in parts:
            if merged and _ABBR.search(merged[-1].split()[-1]):
                merged[-1] = f"{merged[-1]} {p}"
            else:
                merged.append(p)
        parts = merged

        # Second pass: pack sentences without exceeding cap; hard-wrap if needed.
        chunks: list[str] = []
        buf: list[str] = []
        cur = 0
        for p in parts:
            sep = " " if buf else ""
            if cur + len(sep) + len(p) <= cap:
                buf.append(p)
                cur += len(sep) + len(p)
            else:
                if buf:
                    chunks.append(" ".join(buf))
                if len(p) > cap:
                    chunks.extend(Chunker._hard_wrap(p, cap))
                    buf, cur = [], 0
                else:
                    buf, cur = [p], len(p)
        if buf:
            chunks.append(" ".join(buf))
        return chunks

    @staticmethod
    def _hard_wrap(s: str, cap: int) -> list[str]:
        """Hard wrap a long sentence at word boundaries to fit within cap."""
        words = s.split()
        out: list[str] = []
        buf: list[str] = []
        cur = 0
        for w in words:
            sep = " " if buf else ""
            if cur + len(sep) + len(w) <= cap:
                buf.append(w)
                cur += len(sep) + len(w)
            else:
                out.append(" ".join(buf))
                buf, cur = [w], len(w)
        if buf:
            out.append(" ".join(buf).strip(" ,;"))
        return out
