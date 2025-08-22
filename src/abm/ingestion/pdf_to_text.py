"""PDF to text extraction using PyMuPDF (fitz).

Deterministic, local-first extraction with minimal normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass(frozen=True)
class PdfToTextOptions:
    """Options controlling text normalization and separators.

    Attributes:
        dedupe_whitespace: Collapse runs of whitespace to single spaces
            within lines.
        preserve_form_feeds: Insert a form-feed (\f) between pages instead
            of a blank line.
        newline: Newline sequence to use in the output file ("\n" or
            "\r\n").
    """

    dedupe_whitespace: bool = True
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
            doc = fitz.open(pdf_path)  # type: ignore[arg-type]
        except Exception as exc:
            # Map open failures to ValueError to keep a simple contract.
            raise ValueError(f"Cannot open PDF: {pdf_path}") from exc
        try:
            # Use get_text("text") for layout-preserving blocks
            return [page.get_text("text") for page in doc]
        finally:
            doc.close()

    def _clean(self, pages: list[str], options: PdfToTextOptions) -> str:
        """Normalize pages and join with configured separators."""
        norm_pages: list[str] = []
        for raw in pages:
            lines = raw.splitlines()
            if options.dedupe_whitespace:
                lines = [" ".join(line.split()) for line in lines]
            # Rejoin lines with configured newline
            page_text = options.newline.join(lines).strip()
            norm_pages.append(page_text)
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
