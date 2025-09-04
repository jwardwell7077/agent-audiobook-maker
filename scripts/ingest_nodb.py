#!/usr/bin/env python3
"""Minimal ingest helper (no DB stub).

Reads a PDF, extracts raw text and well-done text using abm.ingestion modules,
then writes standard artifacts under the given out dir:
- <stem>_raw.txt
- <stem>_well_done.txt
- <stem>_well_done.jsonl + <stem>_well_done_meta.json

This mirrors dev-mode behavior without invoking any DB insert stub.

Usage:
  python scripts/ingest_nodb.py <pdf_path> <out_dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

from abm.ingestion.pdf_to_raw_text import RawExtractOptions, RawPdfTextExtractor
from abm.ingestion.raw_to_welldone import RawToWellDone, WellDoneOptions
from abm.ingestion.welldone_to_json import WellDoneToJSONL


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("Usage: python scripts/ingest_nodb.py <pdf_path> <out_dir>", file=sys.stderr)
        return 2

    pdf = Path(args[0])
    out_dir = Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)

    extractor = RawPdfTextExtractor()
    pages = extractor.extract_pages(pdf)
    raw_text = extractor.assemble_output(
        pages,
        RawExtractOptions(
            newline="\n",
            preserve_form_feeds=False,
            strip_trailing_spaces=True,
            dedupe_inline_spaces=False,
            fix_short_wraps=False,
            artifact_compat=False,
        ),
    )

    raw_path = out_dir / f"{pdf.stem}_raw.txt"
    raw_path.write_text(raw_text, encoding="utf-8")

    processor = RawToWellDone()
    well = processor.process_text(
        raw_text,
        WellDoneOptions(
            reflow_paragraphs=True,
            dehyphenate_wraps=True,
            dedupe_inline_spaces=True,
            strip_trailing_spaces=True,
        ),
    )
    wd_path = out_dir / f"{pdf.stem}_well_done.txt"
    wd_path.write_text(well, encoding="utf-8")

    # JSONL + meta
    base_name = f"{pdf.stem}_well_done"
    conv = WellDoneToJSONL()
    conv.convert_text(well, base_name=base_name, out_dir=out_dir, ingest_meta_path=None)

    print(f"wrote raw: {raw_path}")
    print(f"wrote well_done: {wd_path}")
    print(f"wrote jsonl/meta: {out_dir / (base_name + '.jsonl')} | {out_dir / (base_name + '_meta.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
