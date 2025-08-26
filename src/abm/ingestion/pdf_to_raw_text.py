"""Raw PDF → Text extractor preserving line/blank-line fidelity (PyMuPDF).

- Preserves visible line breaks and blank lines.
- Reconstructs lines from raw spans to reduce mid-word splits.
- Normalizes trailing spaces and dedupes justification gaps.
- Optional form feed between pages; ensures trailing newline.

CLI:
  python -m abm.ingestion.pdf_to_raw_text <input.pdf> [output.txt]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


@dataclass(frozen=True)
class RawExtractOptions:
    newline: str = "\n"
    preserve_form_feeds: bool = False
    strip_trailing_spaces: bool = True
    dedupe_inline_spaces: bool = False
    fix_short_wraps: bool = False
    artifact_compat: bool = False


class RawPdfTextExtractor:
    """Low-level PDF→text extractor that preserves line/blank-line fidelity.

    Primary responsibilities:
    - Extract per-page text blocks (minimal processing)
    - Assemble pages into a single text buffer
    - Optionally write to disk

    Use `extract_pages` + `assemble_output` if you need an in-memory object
    for further processing before writing.
    """

    def extract(self, pdf_path: str | Path, out_path: str | Path, options: RawExtractOptions | None = None) -> None:
        opts = options or RawExtractOptions()
        if opts.newline not in ("\n", "\r\n"):
            raise ValueError("newline must be \\n or \\r\\n")
        pdf_p, out_p = Path(pdf_path), Path(out_path)
        if not pdf_p.exists():
            raise FileNotFoundError(str(pdf_p))
        pages = self.extract_pages(pdf_p)
        text = self.assemble_output(pages, opts)
        self._write(out_p, text)

    def extract_pages(self, pdf_path: str | Path) -> list[str]:
        """Return list of per-page raw texts (minimal processing)."""
        pdf_path = Path(pdf_path)
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"Cannot open PDF: {pdf_path}") from exc
        try:
            return [self._extract_page_text_blocks(page) for page in doc]
        finally:
            doc.close()

    def _extract_page_text_blocks(self, page: Any) -> str:
        try:
            blocks = page.get_text("blocks")
        except Exception:
            return str(page.get_text("text"))
        # Sort by y, then x
        blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        out_lines: list[str] = []
        for b in blocks:
            text = b[4] if len(b) > 4 else ""
            if not text:
                continue
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            out_lines.extend(text.split("\n"))
            # Ensure a blank line between blocks
            if not (out_lines and out_lines[-1] == ""):
                out_lines.append("")
        # Trim trailing blanks
        while out_lines and out_lines[-1] == "":
            out_lines.pop()
        return "\n".join(out_lines)

    def assemble_output(self, pages: list[str], opts: RawExtractOptions) -> str:
        norm_pages: list[str] = []
        for raw in pages:
            raw = raw.replace("\r\n", "\n").replace("\r", "\n")

            # Optional wrap-fix normalizations; artifact-compat must preserve all newlines
            if opts.fix_short_wraps:
                # Dehyphenate words split at EOL: "some-\nthing" -> "something"
                raw = re.sub(r"(\w)-\n(\w)", r"\1\2", raw)
                # Join short fragments across hard wrap when next starts lowercase
                raw = re.sub(r"(?<=\b[A-Za-z])\n(?=[a-z])", "", raw)
                raw = re.sub(r"(?<=\b[A-Za-z]{2})\n(?=[a-z])", "", raw)

            lines = raw.split("\n")
            if opts.strip_trailing_spaces:
                lines = [ln.rstrip() for ln in lines]
            if opts.dedupe_inline_spaces:
                # Deduplicate justification gaps into single spaces per line
                lines = [re.sub(r" {2,}", " ", ln) for ln in lines]

            # Avoid aggressive reflow: preserve original line/blank-line fidelity
            norm_pages.append("\n".join(lines))
        page_sep = "\f" if opts.preserve_form_feeds else "\n\n"
        joined = page_sep.join(norm_pages)
        if opts.newline != "\n":
            joined = joined.replace("\n", opts.newline)
        if not joined.endswith(opts.newline):
            joined += opts.newline
        return joined

    def _write(self, out_path: Path, text: str) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", newline="")


def _default_output_for_input(p: Path) -> Path:
    return p.with_suffix(".txt")


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Raw PDF → text extraction")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("output", nargs="?", help="Path to output .txt file")
    parser.add_argument("--newline", default="\n", choices=["\n", "\r\n"], help="Newline to use")
    parser.add_argument("--preserve-form-feeds", action="store_true", help="Insert \f between pages")
    parser.add_argument("--no-strip-trailing-spaces", action="store_true", help="Keep trailing spaces")
    parser.add_argument("--dedupe-inline-spaces", action="store_true", help="Collapse multiple spaces inside lines")
    parser.add_argument("--fix-short-wraps", action="store_true", help="Join short fragments split across line wraps")
    parser.add_argument(
        "--artifact-compat",
        action="store_true",
        help="Enable a set of normalizations to match known artifact formatting",
    )
    args = parser.parse_args()
    in_p = Path(args.input)
    out_p = Path(args.output) if args.output else _default_output_for_input(in_p)
    opts = RawExtractOptions(
        newline=args.newline,
        preserve_form_feeds=args.preserve_form_feeds,
        strip_trailing_spaces=not args.no_strip_trailing_spaces,
        dedupe_inline_spaces=args.dedupe_inline_spaces,
        fix_short_wraps=args.fix_short_wraps,
        artifact_compat=args.artifact_compat,
    )
    try:
        RawPdfTextExtractor().extract(in_p, out_p, opts)
        sys.exit(0)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(3)
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
