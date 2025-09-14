#!/usr/bin/env python3
"""
Spot chapters that need attention based on Unknown speaker ratio over Dialogue/Thought spans.

Example:
    python scripts/spot_chapters_attention.py --in data/annotations/private_book/full_gpu_book/combined.json --top 10
"""

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="input", required=True, help="Path to combined.json")
    p.add_argument(
        "--types",
        default="Dialogue,Thought",
        help="Comma-separated span types to include (default: Dialogue,Thought)",
    )
    p.add_argument("--top", type=int, default=10, help="Top N chapters to show")
    return p.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


essential_fields = ("chapter_index", "spans")


def main() -> int:
    args = parse_args()
    doc = load_json(Path(args.input))
    types = {t.strip() for t in args.types.split(",") if t.strip()}

    rows: list[tuple[float, int, str, int, int]] = []
    for ch in doc.get("chapters", []) if isinstance(doc, dict) else []:
        spans = [s for s in (ch.get("spans", []) or []) if s.get("type") in types]
        if not spans:
            continue
        unk = sum(1 for s in spans if s.get("speaker") == "Unknown")
        total = len(spans)
        ratio = (unk / total) if total else 0.0
        rows.append((ratio, int(ch.get("chapter_index", -1)), ch.get("title", ""), total, unk))

    for ratio, idx, title, total, unk in sorted(rows, reverse=True)[: args.top]:
        print(f"{idx:>4} {ratio * 100:5.1f}% unk  ({unk}/{total})  {title}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
