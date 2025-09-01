"""Well-done text → JSONL converter.

Reads a "well-done" text file (paragraphs separated by blank lines) and emits
two artifacts: a JSONL with one record per paragraph block and a sidecar meta
JSON describing the document.

Contract:
- Input: well-done text path; paragraphs are split on blank lines.
- Output (default enriched): <stem>.jsonl where each line is a JSON object with:
        { index, text, line_count, word_count, char_count, start_line, end_line }
    Lite mode (--lite) emits minimal: { index, text }.
- Meta: <stem>_meta.json with fields: book, source_well_done, block_count,
                created_at (UTC ISO), options (from ingest pipeline sidecar if present),
                ingested_from (ingest meta path if available), immutable: true.

This JSONL is intended to be immutable and ingested into Postgres for querying
by the classifier and downstream components.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WDToJSONOptions:
    # When True, write minimal JSONL records {index, text} only.
    lite: bool = False


class WellDoneToJSONL:
    def convert_text(
        self,
        text: str,
        base_name: str,
        out_dir: str | Path,
        ingest_meta_path: str | Path | None = None,
    ) -> dict[str, Path]:
        out_d = Path(out_dir)
        out_d.mkdir(parents=True, exist_ok=True)
        blocks, block_meta = _split_paragraphs_with_meta(text)

        jsonl_path = out_d / (base_name + ".jsonl")
        with jsonl_path.open("w", encoding="utf-8", newline="") as f:
            for i, blk in enumerate(blocks):
                meta = block_meta[i]
                rec = {"index": i, "text": blk}
                # If enriched mode, add metrics and line spans
                rec.update(
                    {
                        "line_count": meta["line_count"],
                        "word_count": meta["word_count"],
                        "char_count": meta["char_count"],
                        "start_line": meta["start_line"],
                        "end_line": meta["end_line"],
                    }
                )
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        meta = _build_meta_for_wd(out_d / (base_name + ".txt"), blocks, ingest_meta_path=ingest_meta_path)
        meta_path = out_d / (base_name + "_meta.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

        return {"jsonl": jsonl_path, "meta": meta_path}

    def convert(
        self,
        well_done_path: str | Path,
        out_dir: str | Path | None = None,
        opts: WDToJSONOptions | None = None,
    ) -> dict[str, Path]:
        opts = opts or WDToJSONOptions()
        wd_p = Path(well_done_path)
        if not wd_p.exists():
            raise FileNotFoundError(str(wd_p))
        out_d = Path(out_dir) if out_dir else wd_p.parent
        text = wd_p.read_text(encoding="utf-8")
        if opts.lite:
            # Minimal records for speed/size-sensitive runs
            blocks = _split_paragraphs(text)
            jsonl_path = out_d / (wd_p.stem + ".jsonl")
            with jsonl_path.open("w", encoding="utf-8", newline="") as f:
                for i, blk in enumerate(blocks):
                    rec = {"index": i, "text": blk}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            meta = _build_meta_for_wd(out_d / (wd_p.stem + ".txt"), blocks, ingest_meta_path=None)
            meta_path = out_d / (wd_p.stem + "_meta.json")
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            return {"jsonl": jsonl_path, "meta": meta_path}
        else:
            return self.convert_text(text, wd_p.stem, out_d)


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text.replace("\r\n", "\n").replace("\r", "\n"))
    return [p for p in parts if p and p.strip()]


def _split_paragraphs_with_meta(text: str) -> tuple[list[str], list[dict[str, int]]]:
    # Normalize newlines and track original lines to compute block line spans
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")

    # Identify blank-line separated blocks by scanning line indices
    blocks: list[str] = []
    meta: list[dict[str, int]] = []
    start = 0
    i = 0

    def is_blank(text_line: str) -> bool:
        return len(text_line.strip()) == 0

    while i <= len(lines):
        end_block = False
        if i == len(lines):
            end_block = True
        elif i > start and is_blank(lines[i]) and is_blank(lines[i - 1]):
            # Already separated by a blank line earlier; continue consuming blanks
            pass
        elif i > start and is_blank(lines[i]):
            # First blank after non-blank content marks end of block
            end_block = True

        if end_block:
            # Collect non-empty trimmed block from start..i-1
            raw = "\n".join(lines[start:i]).strip("\n")
            if raw.strip():
                blk_lines = raw.split("\n")
                text_join = raw
                line_count = len(blk_lines)
                word_count = sum(len(line.split()) for line in blk_lines)
                char_count = len(text_join)
                # 1-based line numbers for spans
                start_line = start + 1
                end_line = i
                blocks.append(text_join)
                meta.append(
                    {
                        "line_count": line_count,
                        "word_count": word_count,
                        "char_count": char_count,
                        "start_line": start_line,
                        "end_line": end_line,
                    }
                )
            # Move start to after this blank-line separator
            i += 1
            start = i
        else:
            i += 1
    return blocks, meta


def _build_meta_for_wd(wd_p: Path, blocks: list[str], ingest_meta_path: str | Path | None = None) -> dict[str, Any]:
    # Attempt to find book name from directory structure if under data/clean/<book>/
    parts = list(wd_p.parts)
    book = None
    try:
        idx = parts.index("clean")
        if idx + 1 < len(parts):
            book = parts[idx + 1]
    except ValueError:
        book = None

    # Try to link ingest meta sidecar if present
    ingest_meta = None
    if ingest_meta_path is not None:
        candidate = Path(ingest_meta_path)
        if candidate.exists():
            ingest_meta = candidate
    else:
        for candidate in [
            wd_p.with_name(wd_p.stem.replace("_well_done", "") + "_ingest_meta.json"),
            wd_p.parent / (wd_p.stem.replace("_well_done", "") + "_ingest_meta.json"),
        ]:
            if candidate.exists():
                ingest_meta = candidate
                break

    options = None
    if ingest_meta and ingest_meta.exists():
        try:
            data = json.loads(ingest_meta.read_text(encoding="utf-8"))
            options = data.get("options")
        except Exception:
            options = None

    return {
        "book": book,
        "source_well_done": str(wd_p),
        "block_count": len(blocks),
        "created_at": datetime.now(UTC).isoformat(),
        "immutable": True,
        "ingested_from": str(ingest_meta) if ingest_meta else None,
        "options": options,
    }


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Well-done text → JSONL + meta")
    parser.add_argument("input", help="Path to well-done .txt")
    parser.add_argument("--out-dir", help="Output directory (defaults to input dir)")
    parser.add_argument("--lite", action="store_true", help="Emit minimal records {index,text} only")
    args = parser.parse_args()
    try:
        opts = WDToJSONOptions(lite=args.lite)
        written = WellDoneToJSONL().convert(Path(args.input), Path(args.out_dir) if args.out_dir else None, opts=opts)
        for k, p in written.items():
            print(f"wrote {k}: {p}")
        sys.exit(0)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
