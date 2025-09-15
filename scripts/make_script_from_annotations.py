#!/usr/bin/env python3
"""Builds a simple render script (items list) from an annotations chapter JSON.

Usage:
  python -m scripts.make_script_from_annotations \
    --chapter-json data/annotations/mvs/full_trf_gpu/chapters/ch_0000.json \
    --out data/tmp/ch_0000.script.json \
    --engine piper \
    --voice en_US-libritts-high \
    --pause-ms 120

The output schema matches abm.audio.render_chapter --script expectations
using an "items" array with engine/voice fields.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter-json", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--engine", type=str, default="piper")
    ap.add_argument("--voice", type=str, default="en_US-libritts-high")
    ap.add_argument("--pause-ms", type=int, default=120)
    args = ap.parse_args(argv)

    data = json.loads(args.chapter_json.read_text(encoding="utf-8"))
    paragraphs = data.get("paragraphs") or []

    # Build items with simple narrations; you can refine later by speaker tagging
    items = []
    for p in paragraphs:
        t = (p or "").strip()
        if not t:
            continue
        items.append(
            {
                "text": t,
                "speaker": "narrator",
                "engine": args.engine,
                "voice": args.voice,
                "refs": [],
                "pause_ms": args.pause_ms,
                "style": "neutral",
            }
        )

    script = {
        "index": int(data.get("chapter_index") or 0),
        "title": data.get("title") or data.get("display_title") or "Chapter",
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} with {len(items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
