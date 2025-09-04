"""Text post-processor: Raw → Well-done (reflow, cleanup).

This module takes raw text (as produced by pdf_to_raw_text) and applies
optional, deterministic normalization to produce a more readable, line-wrapped
text while preserving paragraph boundaries.

Key invariants:
- Paragraph boundaries (blank-line separated) are preserved.
- Inner newlines inside paragraphs may be reflowed by joining to a single line;
    no new line breaks are ever inserted inside a paragraph.
- No semantic changes; only whitespace and hyphenation are altered.

CLI:
  python -m abm.ingestion.raw_to_welldone <input.txt> [output.txt]
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class WellDoneOptions:
    # If True, attempt to join lines within a paragraph respecting sentence/word boundaries
    reflow_paragraphs: bool = True
    # Remove mid-word hyphenation across line breaks (e.g., "some-\nthing" → "something")
    dehyphenate_wraps: bool = True
    # Collapse multiple spaces within a line to a single space
    dedupe_inline_spaces: bool = True
    # Strip trailing spaces at end of lines
    strip_trailing_spaces: bool = True
    # When True, split every non-empty line into its own paragraph (blank-line separated)
    split_each_line: bool = False
    # When True, promote heading-like lines (e.g., "Chapter 4: Title") to standalone paragraphs
    split_headings: bool = False


class RawToWellDone:
    def process_text(self, text: str, opts: WellDoneOptions | None = None) -> str:
        opts = opts or WellDoneOptions()
        paragraphs = self._split_paragraphs(text)
        # First, optionally split heading-like lines out as their own paragraphs
        if opts.split_headings:
            paragraphs = self._apply_split_headings(paragraphs, opts)
        # Optionally explode each line into its own paragraph unit
        if opts.split_each_line:
            exploded = [
                (ln.rstrip() if opts.strip_trailing_spaces else ln)
                for para in paragraphs
                for ln in para.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                if ln and ln.strip()
            ]
            out = [self._process_paragraph(p, opts) for p in exploded]
        else:
            out = [self._process_paragraph(p, opts) for p in paragraphs]
        return "\n\n".join(out) + ("\n" if text.endswith("\n") else "")

    def _apply_split_headings(self, paragraphs: list[str], opts: WellDoneOptions) -> list[str]:
        # Detect heading-like lines: Chapter, Chap., Ch., Prologue, Epilogue (+ optional numbers/titles)
        # Keep it conservative and anchored at line start; apply a modest length guard.
        heading_re = re.compile(
            r"^\s*(?:chapter|chap\.?|ch\.?|prologue|epilogue)\b[\s.:IVXLCDM0-9-]*.*$",
            re.IGNORECASE,
        )
        max_len = 120
        result: list[str] = []
        for para in paragraphs:
            # Normalize newlines and optionally strip trailing spaces per option
            lines = [
                (ln.rstrip() if opts.strip_trailing_spaces else ln)
                for ln in para.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            ]
            if len(lines) <= 1:
                result.append(para)
                continue
            buf: list[str] = []

            def flush_buf() -> None:
                nonlocal buf
                if buf:
                    result.append("\n".join(buf))
                    buf = []

            for ln in lines:
                s = ln.strip()
                if s and len(s) <= max_len and heading_re.match(s):
                    # Found a heading-like line; flush any accumulated text as its own paragraph
                    flush_buf()
                    result.append(ln)
                else:
                    buf.append(ln)
            flush_buf()
        return result

    def _split_paragraphs(self, text: str) -> list[str]:
        parts = re.split(r"\n\s*\n+", text.replace("\r\n", "\n").replace("\r", "\n"))
        return [p for p in parts if p and p.strip()]

    def _process_paragraph(self, para: str, opts: WellDoneOptions) -> str:
        lines = [ln.rstrip() if opts.strip_trailing_spaces else ln for ln in para.splitlines()]
        if opts.dehyphenate_wraps:
            # Merge hyphenated line-break splits: token-\nnext → tokennext
            joined = re.sub(r"(\w)-\n(\w)", r"\1\2", "\n".join(lines))
        else:
            joined = "\n".join(lines)

        # Heuristic: if this looks like a TOC/list with many bullets, split into individual items
        # Treat '•' bullets as list item starts. If 3+ bullets found, explode into separate paragraphs.
        bullet_count = joined.count("•")
        if bullet_count >= 3:
            parts = [seg.strip() for seg in joined.split("•")]
            items = [f"• {seg}" for seg in parts if seg]
            if items:
                text = "\n\n".join(items)
                # Optionally normalize spaces inside items
                if opts.dedupe_inline_spaces:
                    text = re.sub(r" {2,}", " ", text)
                return text

        if opts.reflow_paragraphs:
            # Join single newlines that likely represent wraps, not paragraph breaks
            joined = re.sub(r"(?<=\S)\n(?=\S)", " ", joined)
            # Deduplicate spaces after joining
            if opts.dedupe_inline_spaces:
                joined = re.sub(r" {2,}", " ", joined)
        else:
            if opts.dedupe_inline_spaces:
                joined = "\n".join(re.sub(r" {2,}", " ", ln) for ln in joined.splitlines())
        return joined
