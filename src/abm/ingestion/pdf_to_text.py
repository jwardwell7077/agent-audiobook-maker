"""PDF to text extraction using PyMuPDF (fitz).

Deterministic, local-first extraction with paragraph-safe normalization.
Preserves blank lines between paragraphs and (optionally) reflows hard wraps
inside paragraphs so each paragraph becomes a single line of text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import fitz  # PyMuPDF


@dataclass(frozen=True)
class PdfToTextOptions:
    """Options controlling text normalization and separators.

    Attributes:
        dedupe_whitespace: Collapse runs of whitespace to single spaces
            within lines.
        reflow_paragraphs: Join line-wrapped lines within a paragraph into a
            single line, preserving blank lines between paragraphs.
        dehyphenate_on_wrap: If True, remove hyphenation at line breaks, e.g.,
            "some-\nthing" -> "something" when reflowing paragraphs.
        preserve_form_feeds: Insert a form-feed (\f) between pages instead
            of a blank line.
        newline: Newline sequence to use in the output file ("\n" or
            "\r\n").
    """

    dedupe_whitespace: bool = True
    # Default to preserving original line structure; callers can opt-in to reflow.
    reflow_paragraphs: bool = False
    dehyphenate_on_wrap: bool = True
    preserve_form_feeds: bool = False
    newline: str = "\n"


class PdfToTextExtractor:
    """Extract text from a PDF using PyMuPDF (fitz)."""

    def extract(
        self,
        pdf_path: str | Path,
        out_path: str | Path,
        options: PdfToTextOptions | None = None,
    ) -> None:
        """Extract text from pdf_path and write to out_path.

        Args:
            pdf_path: Path to input PDF.
            out_path: Path to output text file.
            options: Extraction options; if None, defaults are used.
        """
        opts = options or PdfToTextOptions()
        if opts.newline not in ("\n", "\r\n"):
            raise ValueError("newline must be \\n or \\r\\n")

        pdf_p = Path(pdf_path)
        out_p = Path(out_path)
        if not pdf_p.exists():
            raise FileNotFoundError(str(pdf_p))

        pages = self._read(pdf_p)
        text = self._clean(pages, opts)
        self._write(out_p, text)

    def _read(self, pdf_path: Path) -> list[str]:
        """Read pages from PDF as text using fitz."""
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            # Map open failures to ValueError to keep a simple contract.
            raise ValueError(f"Cannot open PDF: {pdf_path}") from exc
        try:
            # Use get_text("text") for layout-preserving blocks
            return [cast(Any, page).get_text("text") for page in doc]
        finally:
            doc.close()

    def _clean(self, pages: list[str], options: PdfToTextOptions) -> str:
        """Normalize pages and join with configured separators.

        - Preserves blank lines between paragraphs.
        - Optionally reflows line-wrapped paragraphs into single lines.
        - Optionally de-hyphenates words broken at line ends.
        """
        norm_pages: list[str] = []
        for raw in pages:
            # Normalize newlines to LF internally
            raw = raw.replace("\r\n", "\n").replace("\r", "\n")

            if not options.reflow_paragraphs:
                # Preserve original line structure and empty lines.
                # Operate line-by-line without collapsing blank lines.
                lines = raw.split("\n")
                if options.dedupe_whitespace:
                    lines = [" ".join(ln.split()) for ln in lines]
                page_text = options.newline.join(lines)
                # Do not strip() to avoid dropping leading/trailing blank lines.
                norm_pages.append(page_text)
                continue

            # Reflow mode: split into paragraphs on blank lines and reflow within paragraphs.
            paragraphs = re.split(r"\n\s*\n", raw)
            paragraphs = [p for p in paragraphs if p.strip()]

            cleaned_paras: list[str] = []
            for para in paragraphs:
                text = para
                # Dehyphenate wrapped words across line break: "some-\nthing" -> "something"
                if options.dehyphenate_on_wrap:
                    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
                # Split lines, trim, optionally dedupe, then join with spaces
                lines = [ln.strip() for ln in text.splitlines()]
                if options.dedupe_whitespace:
                    lines = [" ".join(ln.split()) for ln in lines]
                text = " ".join(ln for ln in lines if ln)

                if options.dedupe_whitespace:
                    text = re.sub(r"\s{2,}", " ", text)
                text = text.strip()
                cleaned_paras.append(text)

            # Join paragraphs with a blank line using configured newline
            page_text = (options.newline * 2).join(cleaned_paras).strip()
            norm_pages.append(page_text)

        # Separator between pages
        sep = "\f" if options.preserve_form_feeds else (options.newline * 2)
        return sep.join(norm_pages) + options.newline

    def _write(self, out_path: Path, text: str) -> None:
        """Write text to ``out_path`` using UTF-8 without newline conversion.

        Args:
            out_path: Destination path for the text file.
            text: Content to write.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", newline="")
