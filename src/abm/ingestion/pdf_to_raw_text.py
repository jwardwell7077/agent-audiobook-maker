"""Raw PDF → Text extractor (line/blank-line fidelity) using PyMuPDF.

Produces a single text output that preserves visible line breaks and blank
lines from the PDF as faithfully as PyMuPDF provides them.

CLI:
  python -m abm.ingestion.pdf_to_raw_text <input.pdf> [output.txt]

If output is omitted, writes next to the input with a .txt extension.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import fitz  # PyMuPDF


@dataclass(frozen=True)
class RawExtractOptions:
    """Options to control raw extraction output.

    Attributes:
        newline: Newline sequence to use ("\n" or "\r\n").
        preserve_form_feeds: If True, insert a form feed (\f) between pages;
            else insert a blank line.
        strip_trailing_spaces: If True, remove trailing spaces at end of lines.
    """

    newline: str = "\n"
    preserve_form_feeds: bool = False
    strip_trailing_spaces: bool = True


class RawPdfTextExtractor:
    """Extract raw text from a PDF preserving line and blank-line fidelity."""

    def extract(
        self,
        pdf_path: str | Path,
        out_path: str | Path,
        options: RawExtractOptions | None = None,
    ) -> None:
        """Extract text from pdf_path and write to out_path.

        Ensures the output ends with a trailing newline.
        """
        opts = options or RawExtractOptions()
        if opts.newline not in ("\n", "\r\n"):
            raise ValueError("newline must be \\n or \\r\\n")

        pdf_p = Path(pdf_path)
        out_p = Path(out_path)
        if not pdf_p.exists():
            raise FileNotFoundError(str(pdf_p))

        pages = self._read_pages(pdf_p)
        text = self._assemble_output(pages, opts)
        self._write(out_p, text)

    def _read_pages(self, pdf_path: Path) -> list[str]:
        """Read pages as layout-preserving text using PyMuPDF."""
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"Cannot open PDF: {pdf_path}") from exc
        try:
            return [cast(Any, page).get_text("text") for page in doc]
        finally:
            doc.close()

    def _assemble_output(self, pages: list[str], opts: RawExtractOptions) -> str:
        norm_pages: list[str] = []
        for raw in pages:
            # Normalize to LF internally
            raw = raw.replace("\r\n", "\n").replace("\r", "\n")
            if opts.strip_trailing_spaces:
                raw = "\n".join(ln.rstrip() for ln in raw.split("\n"))
            norm_pages.append(raw)

        page_sep = "\f" if opts.preserve_form_feeds else "\n\n"
        joined = page_sep.join(norm_pages)

        # Convert newline style if needed
        if opts.newline != "\n":
            joined = joined.replace("\n", opts.newline)

        # Ensure trailing newline
        if not joined.endswith(opts.newline):
            joined += opts.newline
        return joined

    def _write(self, out_path: Path, text: str) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", newline="")


def _default_output_for_input(p: Path) -> Path:
    return p.with_suffix(".txt")


def main(argv: list[str] | None = None) -> int:
    """Simple CLI wrapper. Returns 0 on success, non-zero on error."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Raw PDF → text extraction")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("output", nargs="?", help="Path to output .txt file")
    parser.add_argument("--newline", default="\n", choices=["\n", "\r\n"], help="Newline to use")
    parser.add_argument("--preserve-form-feeds", action="store_true", help="Insert \f between pages")
    parser.add_argument("--no-strip-trailing-spaces", action="store_true", help="Keep trailing spaces")

    args = parser.parse_args(argv)

    in_p = Path(args.input)
    out_p = Path(args.output) if args.output else _default_output_for_input(in_p)

    opts = RawExtractOptions(
        newline=args.newline,
        preserve_form_feeds=args.preserve_form_feeds,
        strip_trailing_spaces=not args.no_strip_trailing_spaces,
    )

    try:
        RawPdfTextExtractor().extract(in_p, out_p, opts)
        return 0
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
