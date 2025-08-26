"""High-level orchestrator: PDF → raw text and well-done text.

This module composes:
- pdf_to_raw_text.RawPdfTextExtractor for minimal, fidelity-first extraction.
- raw_to_welldone.RawToWellDone for reflow and cleanup (paragraph-preserving).

Modes:
- dev: write only raw output (closest to the source), minimal processing.
- both (default): write both raw and well-done outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from abm.ingestion.pdf_to_raw_text import RawExtractOptions, RawPdfTextExtractor
from abm.ingestion.raw_to_welldone import RawToWellDone, WellDoneOptions


@dataclass(frozen=True)
class PipelineOptions:
    # write form-feed between pages in raw
    preserve_form_feeds: bool = False
    # dev mode emits only raw
    mode: str = "both"  # "dev" | "both"
    # well-done options
    reflow_paragraphs: bool = True
    dehyphenate_wraps: bool = True
    dedupe_inline_spaces: bool = True
    strip_trailing_spaces: bool = True
    # No wrapping within blocks; lines may be joined into a single line per paragraph


class PdfToTextPipeline:
    def run(self, pdf_path: str | Path, out_dir: str | Path, opts: PipelineOptions | None = None) -> dict[str, Path]:
        opts = opts or PipelineOptions()
        pdf_p = Path(pdf_path)
        out_d = Path(out_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        # Extract raw (in-memory)
        extractor = RawPdfTextExtractor()
        raw_pages = extractor.extract_pages(pdf_p)
        raw_text = extractor.assemble_output(
            raw_pages,
            RawExtractOptions(
                newline="\n",
                preserve_form_feeds=opts.preserve_form_feeds,
                strip_trailing_spaces=True,
                dedupe_inline_spaces=False,
                fix_short_wraps=False,
                artifact_compat=False,
            ),
        )

        written: dict[str, Path] = {}
        raw_path = out_d / (pdf_p.stem + "_raw.txt")
        raw_path.write_text(raw_text, encoding="utf-8")
        written["raw"] = raw_path

        if opts.mode != "dev":
            processor = RawToWellDone()
            well = processor.process_text(
                raw_text,
                WellDoneOptions(
                    reflow_paragraphs=opts.reflow_paragraphs,
                    dehyphenate_wraps=opts.dehyphenate_wraps,
                    dedupe_inline_spaces=opts.dedupe_inline_spaces,
                    strip_trailing_spaces=opts.strip_trailing_spaces,
                ),
            )
            wd_path = out_d / (pdf_p.stem + "_well_done.txt")
            wd_path.write_text(well, encoding="utf-8")
            written["well_done"] = wd_path

        return written


def _default_out_dir(p: Path) -> Path:
    # If input looks like data/books/<book>/source_pdfs/<pdf>, map to data/clean/<book>/
    parts = list(Path(p).parts)
    try:
        idx = parts.index("books")
        if idx + 1 < len(parts):
            book = parts[idx + 1]
            return Path("data") / "clean" / book
    except ValueError:
        pass
    # Fallback: sibling directory named 'clean' next to input
    return Path(p).parent / "clean"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="PDF → (raw|well-done) text")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("--out-dir", help="Output directory (defaults to data/clean/<book>/)")
    parser.add_argument("--mode", choices=["dev", "both"], default="both")
    parser.add_argument("--preserve-form-feeds", action="store_true")
    # no wrap-width; paragraphs will not be hard-wrapped
    parser.add_argument("--no-reflow", action="store_true")
    parser.add_argument("--no-dehyphenate", action="store_true")
    parser.add_argument("--no-dedupe-spaces", action="store_true")
    parser.add_argument("--no-strip-trailing", action="store_true")
    args = parser.parse_args(argv)

    pdf_p = Path(args.input)
    out_dir = Path(args.out_dir) if args.out_dir else _default_out_dir(pdf_p)

    opts = PipelineOptions(
        preserve_form_feeds=args.preserve_form_feeds,
        mode=args.mode,
        reflow_paragraphs=not args.no_reflow,
        dehyphenate_wraps=not args.no_dehyphenate,
        dedupe_inline_spaces=not args.no_dedupe_spaces,
        strip_trailing_spaces=not args.no_strip_trailing,
    )
    try:
        written = PdfToTextPipeline().run(pdf_p, out_dir, opts)
        for k, p in written.items():
            print(f"wrote {k}: {p}")
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


if __name__ == "__main__":
    raise SystemExit(main())
