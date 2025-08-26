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


class RawToWellDone:
    def process_text(self, text: str, opts: WellDoneOptions | None = None) -> str:
        opts = opts or WellDoneOptions()
        paragraphs = self._split_paragraphs(text)
        out = [self._process_paragraph(p, opts) for p in paragraphs]
        return "\n\n".join(out) + ("\n" if text.endswith("\n") else "")

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

