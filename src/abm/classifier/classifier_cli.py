"""Command-line interface(s) for the Section Classifier.

Entry points:
- TXT: read a plain text file, split into paragraph blocks, classify.
- JSONL: read JSONL produced by welldone_to_json (one block per line), classify.
- Postgres (stub): use --meta to pass ingest/meta info; prints a stub message.

Note: Postgres import is currently stubbed; see TODO markers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from abm.classifier.section_classifier import classify_sections


def _split_blocks(text: str) -> list[str]:
    """Split input into paragraph blocks by blank-line boundaries."""

    parts = re.split(r"\n\s*\n+", text)
    return [p for p in parts if p and p.strip()]


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_blocks_from_jsonl(jsonl_path: Path) -> list[str]:
    blocks: list[str] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            txt = rec.get("text") if isinstance(rec, dict) else None
            if isinstance(txt, str) and txt.strip():
                blocks.append(txt)
    return blocks


def _stub_import_from_postgres(meta: dict[str, Any] | None = None) -> list[str]:
    """TODO: Replace with real DB import once Postgres is ready.

    For now, return an empty list and print a note.
    """
    try:
        print("[DB STUB] Would import blocks from Postgres using meta:", (meta or {}))
    except Exception:
        pass
    return []


def main(argv: list[str] | None = None) -> int:
    """Run the classifier CLI.

    Usage:
      classifier_cli <input.txt|input.jsonl|postgres> <output_dir> [--meta path] [--verbose]
    """

    parser = argparse.ArgumentParser(prog="classifier_cli", add_help=True)
    parser.add_argument("src", help="Path to .txt/.jsonl or 'postgres'")
    parser.add_argument("out_dir", help="Output directory for artifacts")
    parser.add_argument("--meta", dest="meta_path", help="Optional meta JSON (e.g., ingest or jsonl meta)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    ns = parser.parse_args(sys.argv[1:] if argv is None else argv)

    src = ns.src
    out_dir = Path(ns.out_dir)
    meta_dict: dict[str, Any] | None = None
    if ns.meta_path:
        mp = Path(ns.meta_path)
        if mp.exists():
            try:
                meta_dict = json.loads(mp.read_text(encoding="utf-8"))
            except Exception:
                meta_dict = None

    blocks: list[str]
    if src.lower().endswith(".jsonl"):
        in_path = Path(src)
        if not in_path.exists():
            sys.stderr.write(f"Input JSONL not found: {in_path}\n")
            return 3
        blocks = _read_blocks_from_jsonl(in_path)
        if ns.verbose:
            sys.stdout.write(f"Loaded {len(blocks)} blocks from JSONL\n")
    elif src.lower().endswith(".txt"):
        in_path = Path(src)
        if not in_path.exists():
            sys.stderr.write(f"Input text not found: {in_path}\n")
            return 3
        try:
            text = in_path.read_text(encoding="utf-8")
        except Exception as exc:
            sys.stderr.write(f"Failed to read input: {exc}\n")
            return 4
        blocks = _split_blocks(text)
        if ns.verbose:
            sys.stdout.write(f"Loaded {len(blocks)} blocks from text\n")
    elif src.lower() == "postgres":
        # TODO: Implement import-from-DB using ingest meta or document id
        blocks = _stub_import_from_postgres(meta_dict)
        if not blocks:
            sys.stderr.write("No blocks imported from Postgres (stub).\n")
            return 6
    else:
        sys.stderr.write("Unknown input type. Use .txt, .jsonl, or 'postgres'.\n")
        return 2
    outputs = classify_sections({"blocks": blocks})

    try:
        _write_json(
            out_dir / "front_matter.json",
            outputs["front_matter"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "toc.json",
            outputs["toc"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "chapters.json",
            outputs["chapters"],  # type: ignore[index]
        )
        _write_json(
            out_dir / "back_matter.json",
            outputs["back_matter"],  # type: ignore[index]
        )
    except Exception as exc:
        sys.stderr.write(f"Failed to write outputs: {exc}\n")
        return 5

    # print a tiny summary to stdout for interactive usage
    sys.stdout.write("Wrote classifier artifacts to " + str(out_dir) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
