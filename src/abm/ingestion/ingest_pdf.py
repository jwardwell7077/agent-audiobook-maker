"""High-level orchestrator: PDF → raw, well-done text, and JSONL.

This module composes:
- pdf_to_raw_text.RawPdfTextExtractor for minimal, fidelity-first extraction.
- raw_to_welldone.RawToWellDone for reflow and cleanup (paragraph-preserving).

Modes:
- dev: write ALL artifacts (raw, well-done.txt, ingest meta, JSONL + JSONL meta) and also stub a DB insert.
- prod: write NO artifacts; only stub a DB insert (DB not ready yet).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from abm.ingestion.pdf_to_raw_text import RawExtractOptions, RawPdfTextExtractor
from abm.ingestion.raw_to_welldone import RawToWellDone, WellDoneOptions
from abm.ingestion.welldone_to_json import WellDoneToJSONL


@dataclass(frozen=True)
class PipelineOptions:
    # write form-feed between pages in raw
    preserve_form_feeds: bool = False
    # Mode behavior:
    # - dev: write artifacts + stub DB insert
    # - prod: no artifacts, stub DB insert only
    mode: str = "dev"  # "dev" | "prod"
    # well-done options
    reflow_paragraphs: bool = True
    dehyphenate_wraps: bool = True
    dedupe_inline_spaces: bool = True
    strip_trailing_spaces: bool = True
    # Deprecated: JSONL emission flag retained for CLI compatibility; in dev we write JSONL, in prod we don't.
    emit_jsonl: bool = True
    # Deprecated: actual DB insert is currently stubbed (DB not ready)
    insert_to_pg: bool = False


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

        base_name = f"{pdf_p.stem}_well_done"

        if opts.mode == "dev":
            # Write raw
            raw_path = out_d / (pdf_p.stem + "_raw.txt")
            raw_path.write_text(raw_text, encoding="utf-8")
            written["raw"] = raw_path

            # Write well-done text file (for inspection)
            wd_path = out_d / (pdf_p.stem + "_well_done.txt")
            wd_path.write_text(well, encoding="utf-8")
            written["well_done"] = wd_path

            # Write ingest meta sidecar
            meta = _build_meta(pdf_p, out_d, raw_path, wd_path, opts)
            meta_path = out_d / (pdf_p.stem + "_ingest_meta.json")
            meta_path.write_text(_json_dumps(meta) + "\n", encoding="utf-8")
            written["meta"] = meta_path

            # Write JSONL + meta for downstream tools
            conv = WellDoneToJSONL()
            out_paths = conv.convert_text(well, base_name=base_name, out_dir=out_d, ingest_meta_path=meta_path)
            written["jsonl"] = out_paths["jsonl"]
            written["jsonl_meta"] = out_paths["meta"]

            # Stub DB insert (dev also inserts) — TODO: implement actual DB insertion when DB is ready
            _stub_db_insert(mode="dev", base_name=base_name, jsonl_path=out_paths["jsonl"], meta_path=out_paths["meta"])
        else:
            # prod: do NOT write any artifacts; only stub a DB insert using in-memory data
            meta = _build_meta_ephemeral(pdf_p, out_d, opts)
            _stub_db_insert(mode="prod", base_name=base_name, well_text=well, meta=meta)

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


def _build_meta_ephemeral(
    pdf_p: Path,
    out_d: Path,
    opts: PipelineOptions,
) -> dict[str, Any]:
    """Build a minimal meta dict without relying on file artifacts (used in prod mode)."""
    parts = list(pdf_p.parts)
    book = None
    try:
        idx = parts.index("books")
        if idx + 1 < len(parts):
            book = parts[idx + 1]
    except ValueError:
        book = None
    now = datetime.now(UTC).isoformat()
    return {
        "book": book,
        "source_pdf": str(pdf_p),
        "out_dir": str(out_d),
        "mode": opts.mode,
        "options": asdict(opts),
        "created_at": now,
    }


def _stub_db_insert(
    mode: str,
    base_name: str,
    jsonl_path: Path | None = None,
    meta_path: Path | None = None,
    well_text: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Temporary stub for DB insertion.

    TODO: Replace with real Postgres insertion once the DB is ready. In dev mode, we receive file paths
    for JSONL and meta. In prod mode, we avoid writing artifacts and receive in-memory data instead.
    """
    try:
        if mode == "dev":
            print(f"[DB STUB] Would insert JSONL '{jsonl_path}' with meta '{meta_path}' into DB (base={base_name})")
        else:
            # For prod, don't write files; use in-memory content
            print(
                f"[DB STUB] Would insert in-memory data for '{base_name}' into DB "
                f"(blocks from well_text, meta present={meta is not None})"
            )
    except Exception:
        pass


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Ingest PDF → dev: write artifacts; prod: DB insert only (stub)")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("--out-dir", help="Output directory (defaults to data/clean/<book>/)")
    parser.add_argument("--mode", choices=["dev", "prod"], default="dev")
    parser.add_argument("--preserve-form-feeds", action="store_true")
    parser.add_argument("--no-reflow", action="store_true")
    parser.add_argument("--no-dehyphenate", action="store_true")
    parser.add_argument("--no-dedupe-spaces", action="store_true")
    parser.add_argument("--no-strip-trailing", action="store_true")
    parser.add_argument(
        "--emit-jsonl",
        action="store_true",
        help="Deprecated; JSONL is always written as <stem>_well_done.jsonl with meta",
    )
    parser.add_argument("--insert-pg", action="store_true", help="Insert generated JSONL into Postgres if available")
    args = parser.parse_args()

    pdf_p = Path(args.input)
    out_dir = Path(args.out_dir) if args.out_dir else _default_out_dir(pdf_p)

    opts = PipelineOptions(
        preserve_form_feeds=args.preserve_form_feeds,
        mode=args.mode,
        reflow_paragraphs=not args.no_reflow,
        dehyphenate_wraps=not args.no_dehyphenate,
        dedupe_inline_spaces=not args.no_dedupe_spaces,
        strip_trailing_spaces=not args.no_strip_trailing,
        # In dev mode we emit JSONL; in prod we avoid writing any artifacts
        emit_jsonl=True,
        insert_to_pg=args.insert_pg,
    )
    try:
        written = PdfIngestPipeline().run(pdf_p, out_dir, opts)
        for k, p in written.items():
            print(f"wrote {k}: {p}")
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
