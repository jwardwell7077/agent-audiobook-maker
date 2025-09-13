"""Text normalization and safe chunking utilities for TTS."""

from __future__ import annotations

import re

_SMALL_NUMS = {
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
}


class TextNormalizer:
    """Utilities to make raw text friendlier for TTS."""

    _spaces = re.compile(r"[ \t]+")
    _linebreaks = re.compile(r"\s*\n\s*")
    _angle_stat = re.compile(r"<\s*([A-Za-z]+)\s*([0-9]+)\s*/\s*([0-9]+)\s*>")
    _exp = re.compile(r"\b(\d+)\s*exp\b", re.IGNORECASE)
    _bracket_strip = re.compile(r"[<>]")

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize quotes, whitespace, and game-like UI tokens.

        The function performs a lightweight canonicalisation suitable for
        text-to-speech engines:

        * Straighten curly quotes and ellipses to ASCII equivalents.
        * Collapse repeated whitespace and remove extraneous line breaks.
        * Expand stat tokens like ``<HP 10/10>`` into plain English.
        * Expand ``5 exp`` into ``five experience``.

        Args:
            text: Raw input text.

        Returns:
            A normalized string safe for TTS.
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

        def _stat_sub(m: re.Match[str]) -> str:
            label, a, b = m.group(1), int(m.group(2)), int(m.group(3))
            return (
                f"{label.upper()} "
                f"{TextNormalizer._num_to_words(a)} out of {TextNormalizer._num_to_words(b)}"
            )

        s = TextNormalizer._angle_stat.sub(_stat_sub, s)

        def _exp_sub(m: re.Match[str]) -> str:
            n = int(m.group(1))
            return f"{TextNormalizer._num_to_words(n)} experience"

        s = TextNormalizer._exp.sub(_exp_sub, s)

        s = TextNormalizer._bracket_strip.sub("", s)
        return s

    @staticmethod
    def _num_to_words(n: int) -> str:
        """Convert a small integer to words.

        Supports 0..20 and multiples of ten up to 90. Values outside this
        range are returned as digits.
        """
        if n in _SMALL_NUMS:
            return _SMALL_NUMS[n]
        tens_map = {
            30: "thirty",
            40: "forty",
            50: "fifty",
            60: "sixty",
            70: "seventy",
            80: "eighty",
            90: "ninety",
        }
        if n in tens_map:
            return tens_map[n]
        return str(n)


class Chunker:
    """Split text into engine-friendly chunks without breaking quotes/ellipses."""

    @staticmethod
    def split(text: str, *, engine: str, max_chars: int | None = None) -> list[str]:
        """Split ``text`` into chunks appropriate for a TTS engine.

        Args:
            text: Normalized input text.
            engine: Engine name (e.g., ``"piper"``, ``"xtts"``).
            max_chars: Optional hard character cap; defaults are chosen based
                on ``engine``.

        Returns:
            A list of chunks each no longer than ``max_chars``. Splits are
            performed on sentence boundaries and will avoid breaking inside
            balanced double quotes or ellipses.
        """
        default_caps = {"piper": 700, "xtts": 500}
        cap = int(max_chars or default_caps.get(engine, 600))

        sentences = Chunker._sentence_parts(text.strip())

        chunks: list[str] = []
        buf: list[str] = []
        cur_len = 0
        for sent in sentences:
            sep = " " if buf else ""
            if cur_len + len(sep) + len(sent) <= cap:
                buf.append(sent)
                cur_len += len(sep) + len(sent)
            else:
                if buf:
                    chunks.append(" ".join(buf))
                if len(sent) > cap:
                    chunks.extend(Chunker._hard_wrap(sent, cap))
                    buf, cur_len = [], 0
                else:
                    buf, cur_len = [sent], len(sent)
        if buf:
            chunks.append(" ".join(buf))
        return chunks

    @staticmethod
    def _sentence_parts(text: str) -> list[str]:
        """Split ``text`` into sentences while respecting quotes."""
        pattern = re.compile(r'[.!?]["\']?\s+')
        parts: list[str] = []
        start = 0
        for match in pattern.finditer(text):
            next_index = match.end()
            while next_index < len(text) and text[next_index].isspace():
                next_index += 1
            if next_index >= len(text):
                segment = text[start:].strip()
                if segment:
                    parts.append(segment)
                return parts
            next_char = text[next_index]
            if not (next_char.isupper() or next_char in "\"'"):
                continue
            segment = text[start : match.end()].strip()
            if segment.count('"') % 2 != 0:
                continue
            if segment:
                parts.append(segment)
            start = next_index
        if start < len(text):
            segment = text[start:].strip()
            if segment:
                parts.append(segment)
        return parts

    @staticmethod
    def _hard_wrap(s: str, cap: int) -> list[str]:
        """Hard wrap a long string at word boundaries."""
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
            out.append(" ".join(buf))
        return out
