from __future__ import annotations

"""TXT → JSONL structuring utilities.

This module provides a small, deterministic converter that turns normalized
TXT files (produced by the PDF → TXT stage) into a JSON Lines (JSONL)
representation of paragraphs annotated with page numbers.

Determinism: Given the same inputs and options, outputs are byte-identical.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class TxtToJsonOptions:
    """Options for TXT → JSONL conversion.

    Attributes:
        preserve_form_feeds: When True, form feed (\f) splits pages.
            When False, it's treated as literal text.
        newline: Newline sequence to normalize to. Must be "\n" or
            "\r\n".
    """

    preserve_form_feeds: bool = True
    newline: str = "\n"

    def __post_init__(self) -> None:
        if self.newline not in {"\n", "\r\n"}:
            raise ValueError("newline must be \n or \r\n")


class TxtToJsonConverter:
    """Convert normalized TXT into JSONL paragraphs annotated with pages.

    Each JSONL record has keys: ``page`` (1-based), ``para_index`` (0-based
    within page), and ``text`` (paragraph content). Pages are split on form
    feeds (``\f``) when enabled.
    """

    def convert(
        self,
        txt_path: str | Path,
        out_path: str | Path,
        options: TxtToJsonOptions | None = None,
    ) -> None:
        """Convert a TXT file to a JSONL file of paragraphs.

        Args:
            txt_path: Path to UTF-8 TXT input produced by the extractor.
            out_path: Path to write JSONL output (overwritten if exists).
            options: Optional conversion options; defaults are applied when
                omitted.

        Raises:
            FileNotFoundError: When ``txt_path`` does not exist.
            UnicodeDecodeError: If ``txt_path`` is not valid UTF-8.
            ValueError: If options contain invalid values (e.g., newline).
        """
        opts = options or TxtToJsonOptions()
        txt_p = Path(txt_path)
        out_p = Path(out_path)
        text = txt_p.read_text(encoding="utf-8")

        pages = self._split_pages(text, opts)
        with out_p.open("w", encoding="utf-8", newline="\n") as f:
            for page_idx, page_text in enumerate(pages, start=1):
                for para_idx, para in enumerate(
                    self._iter_paragraphs(page_text)
                ):
                    obj = {
                        "page": page_idx,
                        "para_index": para_idx,
                        "text": para,
                    }
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def _split_pages(self, text: str, opts: TxtToJsonOptions) -> list[str]:
        """Split input ``text`` into pages.

        Args:
            text: Full input document text.
            opts: Active conversion options.

        Returns:
            A list of page strings; single element if no split occurs.
        """
        if opts.preserve_form_feeds and "\f" in text:
            return text.split("\f")
        return [text]

    def _iter_paragraphs(self, page_text: str) -> Iterable[str]:
        """Yield normalized paragraphs from a single page string.

        Paragraphs are contiguous runs of non-empty lines, separated by one or
        more blank lines. Within a paragraph, single newlines are preserved.

        Args:
            page_text: The page text to segment.

        Yields:
            Paragraph strings with minimal whitespace normalization applied.
        """
        lines = [self._normalize_ws(line) for line in page_text.splitlines()]
        buf: list[str] = []
        for line in lines:
            if line.strip() == "":
                if buf:
                    yield "\n".join(buf).strip()
                    buf = []
            else:
                buf.append(line.rstrip())
        if buf:
            yield "\n".join(buf).strip()

    def _normalize_ws(self, s: str) -> str:
        """Normalize intra-line whitespace.

        Collapses runs of space characters to a single space and trims trailing
        spaces. Tabs and newlines are preserved (newlines are handled by the
        caller via ``splitlines``).

        Args:
            s: Input string to normalize.

        Returns:
            A normalized string with collapsed spaces and no trailing spaces.
        """
        out = []
        prev_space = False
        for ch in s:
            if ch == " ":
                if not prev_space:
                    out.append(ch)
                prev_space = True
            else:
                out.append(ch)
                prev_space = False
        return "".join(out).rstrip()
