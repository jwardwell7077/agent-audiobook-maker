"""High-level orchestrator: PDF → raw text and well-done text.

This module composes:
- pdf_to_raw_text.RawPdfTextExtractor for minimal, fidelity-first extraction.
- raw_to_welldone.RawToWellDone for reflow and cleanup (paragraph-preserving).

Modes:
- dev: write only raw output (closest to the source), minimal processing.
- both (default): write both raw and well-done outputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from abm.ingestion.pdf_to_raw_text import RawExtractOptions, RawPdfTextExtractor
from abm.ingestion.raw_to_welldone import RawToWellDone, WellDoneOptions


@dataclass(frozen=True)
class PipelineOptions:
    # write form-feed between pages in raw
    preserve_form_feeds: bool = False
    # dev mode instructs pipeline to persist intermediate well-done text as a file
    mode: str = "both"  # "dev" | "both"
    # well-done options
    reflow_paragraphs: bool = True
    dehyphenate_wraps: bool = True
    dedupe_inline_spaces: bool = True
    strip_trailing_spaces: bool = True


class PdfIngestPipeline:
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

        # Always compute well-done in memory; in dev mode we also persist the intermediate file
        wd_path: Path | None = None
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
        if opts.mode in ("dev", "both"):
            wd_path = out_d / (pdf_p.stem + "_well_done.txt")
            wd_path.write_text(well, encoding="utf-8")
            written["well_done"] = wd_path

        # Write a sidecar meta JSON for downstream tools
        meta = _build_meta(pdf_p, out_d, raw_path, wd_path, opts)
        meta_path = out_d / (pdf_p.stem + "_ingest_meta.json")
        meta_path.write_text(_json_dumps(meta) + "\n", encoding="utf-8")
        written["meta"] = meta_path

        return written


def _build_meta(
    pdf_p: Path,
    out_d: Path,
    raw_path: Path,
    wd_path: Path | None,
    opts: PipelineOptions,
) -> dict[str, Any]:
    parts = list(pdf_p.parts)
    book = None
    try:
        idx = parts.index("books")
        if idx + 1 < len(parts):
            book = parts[idx + 1]
    except ValueError:
        book = None
    now = datetime.now(UTC).isoformat()
    meta: dict[str, Any] = {
        "book": book,
        "source_pdf": str(pdf_p),
        "out_dir": str(out_d),
        "mode": opts.mode,
        "options": asdict(opts),
        "created_at": now,
        "raw_path": str(raw_path),
        "raw_sha256": _sha256_file(raw_path),
    }
    if wd_path is not None and wd_path.exists():
        meta.update({"well_done_path": str(wd_path), "well_done_sha256": _sha256_file(wd_path)})
    return meta


def _sha256_file(p: Path) -> str:
    data = p.read_bytes()
    return sha256(data).hexdigest()


def _json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _default_out_dir(p: Path) -> Path:
    parts = list(Path(p).parts)
    try:
        idx = parts.index("books")
        if idx + 1 < len(parts):
            book = parts[idx + 1]
            return Path("data") / "clean" / book
    except ValueError:
        pass
    return Path(p).parent / "clean"


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Ingest PDF → (raw|well-done) text + meta")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("--out-dir", help="Output directory (defaults to data/clean/<book>/)")
    parser.add_argument("--mode", choices=["dev", "both"], default="both")
    parser.add_argument("--preserve-form-feeds", action="store_true")
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
        written = PdfIngestPipeline().run(pdf_p, out_dir, opts)
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
