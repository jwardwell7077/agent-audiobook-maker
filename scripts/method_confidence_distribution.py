#!/usr/bin/env python3
"""
Report method counts and confidence stats for Dialogue/Thought spans.

Example:
    python scripts/method_confidence_distribution.py --in data/annotations/private_book/full_gpu_book/combined.json
"""

import argparse
import json
import numbers
from collections import Counter
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
    p.add_argument("--top", type=int, default=10, help="Show top N methods")
    return p.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    doc = load_json(Path(args.input))
    types = {t.strip() for t in args.types.split(",") if t.strip()}

    method_ctr: Counter[str] = Counter()
    confs: list[float] = []

    for ch in doc.get("chapters", []) if isinstance(doc, dict) else []:
        for s in ch.get("spans", []) or []:
            if s.get("type") in types:
                method_ctr[s.get("method")] += 1
                c = s.get("confidence")
                if isinstance(c, numbers.Real):
                    confs.append(float(c))

    top = method_ctr.most_common(args.top)
    print("Method counts:", top)

    if confs:
        avg = sum(confs) / len(confs)
        print("Conf avg/min/max:", (avg, min(confs), max(confs)))
    else:
        print("Conf avg/min/max:", (0, 0, 0))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
