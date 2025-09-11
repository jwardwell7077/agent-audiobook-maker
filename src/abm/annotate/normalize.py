from __future__ import annotations

import enum
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


class LineTag(str, enum.Enum):
    """Structured label for per-paragraph line classification."""

    HEADING = "Heading"
    SYSTEM_ANGLE = "SystemAngle"
    SYSTEM_SQUARE = "SystemSquare"
    SECTION_BREAK = "SectionBreak"
    META = "Meta"
    NONE = "None"


@dataclass
class InlineTag:
    """Inline structural token span inside a non-system paragraph."""

    start: int
    end: int
    tag: str  # e.g., "SystemInlineAngle", "SystemInlineSquare"


@dataclass
class NormalizerConfig:
    """Configuration for ChapterNormalizer behavior."""

    join_with: str = "\n\n"
    strip_control_chars: bool = True
    unicode_normalization: Literal["NFC", "NFD", "NFKC", "NFKD"] | None = None
    treat_heading_as_removable: bool = False  # If True, drop heading paragraph 0
    meta_keywords: tuple[str, ...] = (
        "patreon",
        "p.a.t.r.e.o.n",
        "instagram",
        "author's note",
        "author’s note",
        "vote",
        "webnovel",
        "discord",
        "donate",
        "paypal",
        "privilege",
    )


@dataclass
class NormalizeReport:
    """Summary of normalization actions and counts for one chapter."""

    is_heading: bool = False
    removed_heading_index: int | None = None
    spaced_angle_fixes: int = 0
    counts: dict[str, int] = field(
        default_factory=lambda: {
            LineTag.SYSTEM_ANGLE.value: 0,
            LineTag.SYSTEM_SQUARE.value: 0,
            LineTag.SECTION_BREAK.value: 0,
            LineTag.META.value: 0,
            LineTag.HEADING.value: 0,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict."""

        out = asdict(self)
        out["counts"] = dict(self.counts)
        return out


class ChapterNormalizer:
    """Normalize and structurally tag a chapter object."""

    # --- Patterns (compiled once) ---
    RE_HEADING = re.compile(r"^Chapter\s+\d+[:\s]", re.IGNORECASE)

    # Scene breaks and meta lines
    RE_SCENE_BREAK = re.compile(r"^\s*\*{3,}\s*$")
    RE_META = re.compile(
        r"(patr?eon|p\.a\.t\.r\.e\.o\.n|instagram|author.?s note|vote|webnovel|discord|donate|paypal|privilege)",
        re.IGNORECASE,
    )

    # System lines: single token with optional trailing punctuation
    RE_SYSTEM_ANGLE_LINE = re.compile(r"^\s*<[^>]+>\s*[.?!]?\s*$")
    RE_SYSTEM_SQUARE_LINE = re.compile(r"^\s*\[[^\]]+\]\s*[.?!]?\s*$")

    # System lines: multiple tokens only
    RE_SYSTEM_ANGLE_MULTI = re.compile(r"^\s*(<[^>]+>\s*){2,}\s*$")
    RE_SYSTEM_SQUARE_MULTI = re.compile(r"^\s*(\[[^\]]+\]\s*){2,}\s*$")

    # Inline system tokens (inside normal lines)
    RE_INLINE_ANGLE = re.compile(r"<[^>]+>")
    RE_INLINE_SQUARE = re.compile(r"\[[^\]]+\]")

    # Control characters (including NBSP / BOM via unicode filter)
    RE_CONTROL = re.compile(r"[\u0000-\u001F\u007F\u0080-\u009F\uFEFF]")

    def __init__(self, config: NormalizerConfig | None = None) -> None:
        """Initialize the normalizer with an optional config."""

        self.config = config or NormalizerConfig()

    # --------------- Public API ---------------

    def normalize(self, chapter: dict[str, Any]) -> dict[str, Any]:
        """Normalize and tag a single chapter.

        Args:
            chapter: Chapter dictionary with at least a `paragraphs` list and a `title`.

        Returns:
            A new chapter dict including:
              - `text` (joined with stable LF line endings),
              - `display_title`,
              - `line_tags` (parallel to `paragraphs`),
              - `inline_tags` (mapping of paragraph index -> list of inline spans),
              - `normalize_report` (manifest),
              - `text_normalized: True`
        """

        paragraphs = list(chapter.get("paragraphs") or [])
        title = chapter.get("title", "")

        # 1) Trim trailing spaces (safe; does not change offsets within line)
        paragraphs = [p.rstrip() for p in paragraphs]

        # 2) Basic sanitization: control chars & optional unicode normalization
        if self.config.strip_control_chars:
            paragraphs = [self._strip_control_chars(p) for p in paragraphs]
        if self.config.unicode_normalization:
            paragraphs = [unicodedata.normalize(self.config.unicode_normalization, p) for p in paragraphs]

        report = NormalizeReport()

        # 3) Identify heading at paragraph 0 (do not remove unless configured)
        is_heading = bool(paragraphs and self.RE_HEADING.match(paragraphs[0]))
        report.is_heading = is_heading

        removed_indices: list[int] = []
        if is_heading and self.config.treat_heading_as_removable:
            paragraphs.pop(0)
            removed_indices.append(0)
            report.removed_heading_index = 0

        # 4) Per-line classification, angle-edge fixes on SystemAngle lines, inline token capture
        line_tags: list[LineTag] = []
        inline_tags: dict[int, list[InlineTag]] = {}
        spaced_angle_fixes = 0

        for idx, raw_line in enumerate(paragraphs):
            tag = self._classify_line(raw_line)

            # For counting, also mark if the very first (pre-removal) line was a heading
            if idx == 0 and is_heading and not self.config.treat_heading_as_removable:
                report.counts[LineTag.HEADING.value] += 1

            fixed_line = raw_line

            if tag == LineTag.SYSTEM_ANGLE:
                # Normalize edges in all tokens on a system angle line.
                fixed_line, nfix = self._normalize_system_angle_line(fixed_line)
                spaced_angle_fixes += nfix
            elif tag == LineTag.SYSTEM_SQUARE:
                # No edge fix needed for square tokens, keep as-is (includes trailing punctuation).
                pass
            else:
                # Non-system lines: record inline tokens (do not rewrite).
                spans = self._find_inline_system_tokens(fixed_line)
                if spans:
                    inline_tags[idx] = spans

            line_tags.append(tag)
            paragraphs[idx] = fixed_line

            # Update counts
            if tag in (LineTag.SYSTEM_ANGLE, LineTag.SYSTEM_SQUARE, LineTag.SECTION_BREAK, LineTag.META):
                report.counts[tag.value] += 1

        report.spaced_angle_fixes = spaced_angle_fixes

        # 5) Produce joined text with LF line endings
        text = self.config.join_with.join(paragraphs)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 6) Compose output chapter (non-destructive: keep original title; add display_title)
        out = dict(chapter)
        out["paragraphs"] = paragraphs
        out["text"] = text
        out["display_title"] = self._display_title(title)
        out["line_tags"] = [t.value for t in line_tags]
        # serialize inline tags
        out["inline_tags"] = {str(k): [asdict(span) for span in v] for k, v in inline_tags.items()}
        out["normalize_report"] = report.to_dict()
        out["text_normalized"] = True
        if removed_indices:
            out["removed_paragraph_indices"] = removed_indices
        return out

    # --------------- Internals ---------------

    def _classify_line(self, line: str) -> LineTag:
        """Classify a single paragraph line into a structural tag."""

        if self.RE_SCENE_BREAK.match(line):
            return LineTag.SECTION_BREAK
        if self.RE_META.search(line):
            return LineTag.META
        if self.RE_SYSTEM_ANGLE_LINE.match(line) or self.RE_SYSTEM_ANGLE_MULTI.match(line):
            return LineTag.SYSTEM_ANGLE
        if self.RE_SYSTEM_SQUARE_LINE.match(line) or self.RE_SYSTEM_SQUARE_MULTI.match(line):
            return LineTag.SYSTEM_SQUARE
        if self.RE_HEADING.match(line):
            return LineTag.HEADING
        return LineTag.NONE

    def _normalize_system_angle_line(self, line: str) -> tuple[str, int]:
        """Strip inner-edge spaces inside < ... > tokens on a system angle line.

        Preserves any trailing punctuation following the last token.

        Examples:
            '<  Level 1  >'         -> '<Level 1>'
            '<A> < B >.'            -> '<A> <B>.'
            '   <  User:  Quinn > ' -> '<User:  Quinn>'
        """

        fixes = 0

        # Separate trailing punctuation (., ?, !) if present at the very end.
        trailing_punct = ""
        m = re.match(r"^(.*?)([.?!])\s*$", line)
        core = line
        if m:
            core, trailing_punct = m.group(1), m.group(2)

        # Fix every < ... > token in the core string by trimming spaces at edges only.
        def _trim_token(match: re.Match[str]) -> str:
            nonlocal fixes
            inner = match.group(1)
            trimmed = inner.strip()
            if trimmed != inner:
                fixes += 1
            return f"<{trimmed}>"

        core_fixed = re.sub(r"<\s*(.*?)\s*>", _trim_token, core)

        fixed_line = f"{core_fixed}{trailing_punct}"
        return fixed_line, fixes

    def _find_inline_system_tokens(self, line: str) -> list[InlineTag]:
        """Return inline system token spans inside a normal line."""

        spans = [
            InlineTag(start=m.start(), end=m.end(), tag="SystemInlineAngle")
            for m in self.RE_INLINE_ANGLE.finditer(line)
        ]
        spans.extend(
            InlineTag(start=m.start(), end=m.end(), tag="SystemInlineSquare")
            for m in self.RE_INLINE_SQUARE.finditer(line)
        )
        return spans

    def _strip_control_chars(self, s: str) -> str:
        """Remove control characters and BOM/NBSP-like codepoints."""

        return self.RE_CONTROL.sub("", s)

    @staticmethod
    def _display_title(title: str) -> str:
        """Compute a display title without mutating the original title."""

        # Keep it simple and predictable; callers can customize later if needed.
        return title.title() if title else title


# --------- Convenience function (backwards-compatible) ---------


def normalize_chapter_text(chapter: dict[str, Any], config: NormalizerConfig | None = None) -> dict[str, Any]:
    """Backwards-compatible helper: normalize a chapter dict with defaults.

    This wrapper preserves the previous functional API you may have used.
    """

    normalizer = ChapterNormalizer(config=config)
    return normalizer.normalize(chapter)


# Usage example:
# from abm.annotate.normalize import ChapterNormalizer, NormalizerConfig
#
# config = NormalizerConfig(
#     treat_heading_as_removable=False,
#     unicode_normalization=None,
# )
#
# normalizer = ChapterNormalizer(config)
# normalized_chapter = normalizer.normalize(chapter_dict)
#
# Fields available in `normalized_chapter`:
# - text: joined paragraphs with LF line endings
# - line_tags: per paragraph classification
# - inline_tags: inline system token spans
# - display_title: Title-cased UI label
# - normalize_report: counts and fixes summary
# - text_normalized: True
