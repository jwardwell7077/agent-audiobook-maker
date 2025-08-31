"""Well-done text → JSONL converter.

Reads a "well-done" text file (paragraphs separated by blank lines) and
emits a .jsonl with one record per paragraph block, plus a sidecar immutable
meta JSON describing the document.

Contract:
- Input: well-done text path; paragraphs are split on blank lines.
- Output: <stem>_well_done.jsonl where each line is a JSON object:
    {
        index: number,
        text: string,
        line_count: number,         # lines in this block
        char_count: number,         # characters in this block
        word_count: number,         # whitespace-delimited tokens in this block
        start_line: number,         # 1-based start line in the original document
        end_line: number            # 1-based end line (inclusive)
    }
- Meta: <stem>_well_done_meta.json with fields: book, source_well_done, block_count,
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
    # Reserved for future toggles (e.g., additional normalizations). Keep minimal.
    pass


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
        blocks = _split_paragraphs_with_lines(text)

        jsonl_path = out_d / (base_name + ".jsonl")
        with jsonl_path.open("w", encoding="utf-8", newline="") as f:
            for i, blk in enumerate(blocks):
                rec = {
                    "index": i,
                    "text": blk["text"],
                    "line_count": blk["line_count"],
                    "char_count": blk["char_count"],
                    "word_count": blk["word_count"],
                    "start_line": blk["start_line"],
                    "end_line": blk["end_line"],
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        meta = _build_meta_for_wd(out_d / (base_name + ".txt"), blocks, ingest_meta_path=ingest_meta_path)
        meta_path = out_d / (base_name + "_meta.json")
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

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
        return self.convert_text(text, wd_p.stem, out_d)


from typing import Any, List as _List, Dict as _Dict


def _split_paragraphs_with_lines(text: str) -> list[dict[str, Any]]:
    """Split well-done text into paragraph blocks and record line spans.

    Returns a list of dicts: {
      text: str,
      lines: list[str],
      start_line: int,  # 1-based
      end_line: int,    # inclusive
    }
    """
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    out: list[dict[str, Any]] = []
    i = 0
    L = len(lines)
    line_no = 1  # 1-based numbering for original doc
    while i < L:
        # skip blank lines between paragraphs
        while i < L and (lines[i].strip() == ""):
            i += 1
            line_no += 1
        if i >= L:
            break
        start_ln = line_no
        buf: list[str] = []
        while i < L and (lines[i].strip() != ""):
            buf.append(lines[i])
            i += 1
            line_no += 1
        end_ln = line_no - 1
        text_block = "\n".join(buf)
        if text_block.strip():
            out.append({
                "text": text_block,
                "lines": buf,
                "start_line": start_ln,
                "end_line": end_ln,
                "line_count": len(buf),
                "char_count": len(text_block),
                "word_count": _word_count(text_block),
            })
        # loop continues; i points at a blank line or end; consume separator blanks in next iteration
    return out


def _word_count(s: str) -> int:
    # Count non-whitespace token groups as words
    return len(re.findall(r"\S+", s))


def _build_meta_for_wd(wd_p: Path, blocks: list[Any], ingest_meta_path: str | Path | None = None) -> dict[str, Any]:
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
    args = parser.parse_args()
    try:
        written = WellDoneToJSONL().convert(Path(args.input), Path(args.out_dir) if args.out_dir else None)
        for k, p in written.items():
            print(f"wrote {k}: {p}")
        sys.exit(0)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
