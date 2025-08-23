"""Thin CLI for PDF to text extraction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from abm.ingestion.pdf_to_text import PdfToTextExtractor, PdfToTextOptions


def main(argv: list[str] | None = None) -> int:
    """Run the PDF→Text CLI.

    Args:
        argv: Optional list of command-line arguments. When ``None``,
            arguments are read from ``sys.argv``.

    Returns:
        Process exit code: ``0`` on success, non-zero on error.
    """
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF using PyMuPDF (fitz).",
    )
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("output", help="Path to output .txt file")
    parser.add_argument(
        "--no-dedupe-whitespace",
        action="store_true",
        help="Disable whitespace deduplication",
    )
    parser.add_argument(
        "--preserve-form-feeds",
        action="store_true",
        help="Insert form feed (\\f) between pages",
    )
    parser.add_argument(
        "--newline",
        default="\n",
        choices=["\n", "\r\n"],
        help="Newline to use in output",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help=(
            "Dev mode: also write a human-readable copy with double newlines "
            "(suffix _nopp.txt) while preserving the main artifact"
        ),
    )

    args = parser.parse_args(argv)

    opts = PdfToTextOptions(
        dedupe_whitespace=not args.no_dedupe_whitespace,
        preserve_form_feeds=args.preserve_form_feeds,
        newline=args.newline,
    )

    out_path = Path(args.output)
    try:
        PdfToTextExtractor().extract(Path(args.input), out_path, opts)
        if args.dev:
            # Also create a human-readable copy with double newlines,
            # replacing form-feeds
            try:
                content = out_path.read_text(encoding="utf-8")
            except Exception:
                content = ""
            human = out_path.with_name(out_path.stem + "_nopp" + out_path.suffix)
            human_text = content.replace("\f", opts.newline * 2)
            human.write_text(human_text, encoding="utf-8", newline="")
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
