from __future__ import annotations

import enum
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


class SpanType(str, enum.Enum):
    """Span categories emitted by the Segmenter."""

    NARRATION = "Narration"
    DIALOGUE = "Dialogue"
    THOUGHT = "Thought"
    SYSTEM = "System"
    META = "Meta"
    SECTION_BREAK = "SectionBreak"
    HEADING = "Heading"


@dataclass
class Span:
    """A contiguous piece of text with a semantic label and absolute offsets."""

    start: int
    end: int
    type: SpanType
    text: str
    para_index: int
    subtype: str | None = None
    notes: str | None = None


@dataclass
class SegmenterConfig:
    """Configuration for the Segmenter behavior."""

    join_with: str = "\n\n"
    treat_single_quotes_as_thought: bool = True
    merge_adjacent_same_type: bool = True
    include_heading: bool = True
    include_meta: bool = True
    include_section_break: bool = True
    include_system_lines: bool = True
    include_system_inline: bool = True


class Segmenter:
    """Produce offset-accurate spans from a normalized chapter.

    Expects the chapter to be normalized by ChapterNormalizer:
      - `paragraphs`: list[str]
      - `text`: single LF-joined string of all paragraphs
      - `line_tags`: per-paragraph line tag labels (e.g., "SystemAngle", "Meta", ...)
      - `inline_tags`: { str(para_index) : [ {start, end, tag}, ... ] }

    The segmenter overlays line-level System/Meta/SectionBreak/Heading spans,
    then scans remaining paragraphs with a quote state-machine to carve Dialogue
    and Thought spans out of Narration.

    Usage:
        seg = Segmenter()
        spans = seg.segment(chapter_dict)
    """

    _OPEN_D = {'"', "“"}
    _CLOSE_D = {'"', "”"}
    _OPEN_S = {"'", "‘"}
    _CLOSE_S = {"'", "’"}

    def __init__(self, config: SegmenterConfig | None = None) -> None:
        self.config = config or SegmenterConfig()

    def segment(self, chapter: dict[str, Any]) -> list[Span]:
        """Segment a normalized chapter into labeled spans with absolute offsets.

        Args:
            chapter: Normalized chapter dict from ChapterNormalizer.

        Returns:
            A list of Span objects, sorted by `start`. Adjacent Narration spans
            are optionally merged by configuration.
        """

        paragraphs: list[str] = list(chapter.get("paragraphs") or [])
        line_tags: list[str] = list(chapter.get("line_tags") or [])
        inline_tags: dict[str, list[dict[str, Any]]] = dict(chapter.get("inline_tags") or {})

        para_starts = self._compute_paragraph_starts(paragraphs, self.config.join_with)
        spans: list[Span] = []

        for pi, (ptext, tag) in enumerate(zip(paragraphs, line_tags, strict=True)):
            abs_start = para_starts[pi]
            abs_end = abs_start + len(ptext)

            if tag == "Heading" and self.config.include_heading:
                spans.append(Span(abs_start, abs_end, SpanType.HEADING, ptext, pi))
                continue
            if tag == "Meta" and self.config.include_meta:
                spans.append(Span(abs_start, abs_end, SpanType.META, ptext, pi))
                continue
            if tag == "SectionBreak" and self.config.include_section_break:
                spans.append(Span(abs_start, abs_end, SpanType.SECTION_BREAK, ptext, pi))
                continue
            if tag in {"SystemAngle", "SystemSquare"} and self.config.include_system_lines:
                subtype = "LineAngle" if tag == "SystemAngle" else "LineSquare"
                spans.append(Span(abs_start, abs_end, SpanType.SYSTEM, ptext, pi, subtype=subtype))
                continue

            spans.extend(self._segment_paragraph(pi, ptext, abs_start, inline_tags.get(str(pi), [])))

        spans = sorted(spans, key=lambda s: (s.start, s.end))
        if self.config.merge_adjacent_same_type:
            spans = self._merge_adjacent(spans)

        return spans

    def _segment_paragraph(
        self,
        para_index: int,
        ptext: str,
        abs_start: int,
        paragraph_inline_tags: list[dict[str, Any]],
    ) -> list[Span]:
        """Segment a single paragraph into Narration + overlays."""

        para_spans: list[Span] = [Span(abs_start, abs_start + len(ptext), SpanType.NARRATION, ptext, para_index)]

        for it in paragraph_inline_tags or []:
            rel_s, rel_e = int(it["start"]), int(it["end"])
            tag = str(it.get("tag", "SystemInlineAngle"))
            subtype = "InlineAngle" if "Angle" in tag else "InlineSquare"
            sys_span = Span(
                abs_start + rel_s,
                abs_start + rel_e,
                SpanType.SYSTEM,
                ptext[rel_s:rel_e],
                para_index,
                subtype=subtype,
            )
            para_spans = self._overlay_cut(para_spans, sys_span)

        for qspan in self._iter_quote_spans(ptext, abs_start, para_index):
            para_spans = self._overlay_cut(para_spans, qspan)

        return para_spans

    def _iter_quote_spans(self, ptext: str, abs_start: int, para_index: int) -> Iterable[Span]:
        """Yield Dialogue/Thought spans (absolute) found within a paragraph."""

        i = 0
        n = len(ptext)
        while i < n:
            ch = ptext[i]
            if ch in self._OPEN_D:
                j, note = self._scan_until(ptext, i + 1, self._CLOSE_D)
                yield Span(abs_start + i, abs_start + j + 1, SpanType.DIALOGUE, ptext[i:j + 1], para_index, notes=note)
                i = j + 1
                continue
            if ch in self._OPEN_S and not self._is_apostrophe(ptext, i):
                j, note = self._scan_until(ptext, i + 1, self._CLOSE_S)
                span_type = SpanType.THOUGHT if self.config.treat_single_quotes_as_thought else SpanType.DIALOGUE
                yield Span(abs_start + i, abs_start + j + 1, span_type, ptext[i:j + 1], para_index, notes=note)
                i = j + 1
                continue
            i += 1

    @staticmethod
    def _is_apostrophe(s: str, i: int) -> bool:
        """Return True if s[i] is an apostrophe inside a word (not a quote)."""

        return i > 0 and i + 1 < len(s) and s[i - 1].isalpha() and s[i + 1].isalpha()

    @staticmethod
    def _scan_until(s: str, start: int, closers: Iterable[str]) -> tuple[int, str | None]:
        """Scan forward from `start` until we hit any `closers` or end-of-string."""

        j = start
        n = len(s)
        while j < n and s[j] not in closers:
            j += 1
        if j >= n:
            return n - 1, "quote_mismatch"
        return j, None

    @staticmethod
    def _compute_paragraph_starts(paragraphs: list[str], join_with: str) -> list[int]:
        """Compute absolute start offsets for each paragraph given the joiner."""

        starts: list[int] = []
        cursor = 0
        for idx, p in enumerate(paragraphs):
            starts.append(cursor)
            cursor += len(p)
            if idx != len(paragraphs) - 1:
                cursor += len(join_with)
        return starts

    @staticmethod
    def _overlay_cut(bases: list[Span], overlay: Span) -> list[Span]:
        """Cut `overlay` out of any Narration spans it overlaps; keep others intact."""

        out: list[Span] = []
        a, b = overlay.start, overlay.end
        for base in bases:
            if base.type is not SpanType.NARRATION:
                out.append(base)
                continue
            s0, s1 = base.start, base.end
            if b <= s0 or a >= s1:
                out.append(base)
                continue
            if s0 < a:
                left_text = base.text[: a - s0]
                out.append(Span(s0, a, SpanType.NARRATION, left_text, base.para_index))
            out.append(overlay)
            if b < s1:
                right_text = base.text[b - s0 :]
                out.append(Span(b, s1, SpanType.NARRATION, right_text, base.para_index))
        return sorted(out, key=lambda s: (s.start, s.end))

    def _merge_adjacent(self, spans: list[Span]) -> list[Span]:
        """Merge adjacent spans of the same type (e.g., Narration)."""

        if not spans:
            return spans
        merged: list[Span] = [spans[0]]
        for s in spans[1:]:
            last = merged[-1]
            if last.type == s.type and last.end == s.start and last.subtype == s.subtype:
                merged[-1] = Span(
                    last.start,
                    s.end,
                    last.type,
                    last.text + s.text,
                    last.para_index,
                    last.subtype,
                    last.notes,
                )
            else:
                merged.append(s)
        return merged


def segment_spans(chapter: dict[str, Any], config: SegmenterConfig | None = None) -> list[dict[str, Any]]:
    """Functional wrapper to keep compatibility with earlier code paths."""

    seg = Segmenter(config)
    spans = seg.segment(chapter)
    return [
        {
            "start": s.start,
            "end": s.end,
            "type": s.type.value,
            "text": s.text,
            "para_index": s.para_index,
            "subtype": s.subtype,
            "notes": s.notes,
        }
        for s in spans
    ]
