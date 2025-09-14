#!/usr/bin/env python3
"""
Count Unknown speakers across Dialogue/Thought spans in a combined annotations JSON.

Example:
    python scripts/count_unknown_speakers.py --in data/annotations/private_book/full_gpu_book/combined.json

Exit codes:
    0 on success, 1 on file/read/parse error.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--in",
        dest="input",
        required=True,
        help="Path to combined annotations JSON (e.g., combined.json)",
    )
    p.add_argument(
        "--types",
        default="Dialogue,Thought",
        help="Comma-separated span types to include (default: Dialogue,Thought)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the numeric summary line.",
    )
    return p.parse_args()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)


def count_unknown(doc: Any, types: set[str]) -> tuple[int, int]:
    chapters = doc.get("chapters", []) if isinstance(doc, dict) else []
    total = 0
    unknown = 0
    for ch in chapters:
        for s in ch.get("spans", []) or []:
            if s.get("type") in types:
                total += 1
                if s.get("speaker") == "Unknown":
                    unknown += 1
    return unknown, total


def main() -> int:
    args = parse_args()
    path = Path(args.input)
    doc = load_json(path)

    types: set[str] = {t.strip() for t in args.types.split(",") if t.strip()}
    unknown, total = count_unknown(doc, types)

    if total == 0:
        print("No dialogue spans found")
        return 0

    ratio = unknown / total if total else 0.0
    line = f"Unknown {unknown}/{total} = {ratio:.1%}"
    print(line)

    if not args.quiet:
        print(f"Included types: {sorted(types)}")
        print(f"File: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
