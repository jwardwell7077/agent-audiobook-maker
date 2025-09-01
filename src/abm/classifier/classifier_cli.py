from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from .section_classifier import classify_blocks


def _iter_blocks_from_text(text: str) -> list[dict]:
    """Convert plain text into enriched JSONL-like blocks (one block per line).

    We deliberately emit one block per non-empty line so that TOC headings and
    TOC item lines are independently detectable by the classifier.
    """
    blocks: list[dict] = []
    line_cursor = 1
    idx = 0
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        # Always advance line counter even if we skip empty lines
        if line.strip():
            blocks.append(
                {
                    "index": idx,
                    "text": line,
                    "line_count": 1,
                    "word_count": len(line.split()),
                    "char_count": len(line),
                    "start_line": line_cursor,
                    "end_line": line_cursor,
                }
            )
            idx += 1
        line_cursor += 1
    return blocks


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Section classifier CLI (text or JSONL)")
    p.add_argument("input_path", help="Input .txt (paragraphs) or .jsonl (blocks)")
    p.add_argument("output_dir", help="Output directory for artifacts")
    args = p.parse_args(argv)

    in_path = Path(args.input_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tmp_jsonl: Path | None = None
    try:
        if in_path.suffix.lower() == ".jsonl":
            jsonl_path = in_path
        else:
            # Treat any non-.jsonl as plain text input
            text = in_path.read_text(encoding="utf-8")
            blocks = _iter_blocks_from_text(text)
            # Persist to a temp JSONL file alongside outputs
            fd, tmp_name = tempfile.mkstemp(prefix="blocks_", suffix=".jsonl", dir=str(out_dir))
            os.close(fd)
            tmp_jsonl = Path(tmp_name)
            with tmp_jsonl.open("w", encoding="utf-8") as f:
                for obj in blocks:
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            jsonl_path = tmp_jsonl

        result = classify_blocks(str(jsonl_path))

        _write_json(out_dir / "toc.json", result["toc"])  # type: ignore[index]
        _write_json(out_dir / "chapters.json", result["chapters"])  # type: ignore[index]
        _write_json(out_dir / "front_matter.json", result["front_matter"])  # type: ignore[index]
        _write_json(out_dir / "back_matter.json", result["back_matter"])  # type: ignore[index]

        # Tiny summary for interactive usage
        print(f"Wrote artifacts to {out_dir}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 2
    finally:
        if tmp_jsonl and tmp_jsonl.exists():
            try:
                tmp_jsonl.unlink()
            except Exception:
                # Non-fatal cleanup failure
                pass


if __name__ == "__main__":
    raise SystemExit(main())
