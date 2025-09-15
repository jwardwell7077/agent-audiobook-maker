#!/usr/bin/env python3
"""Render an entire book from annotations by piping through the chapter CLI.

This script:
- Scans an annotations chapters directory (e.g., data/annotations/.../chapters)
- For each chapter JSON, builds a simple Piper-based script (items)
- Invokes abm.audio.render_chapter for each chapter, writing a single book manifest

Usage:
  python -m scripts.render_book_from_annotations \
    --chapters-dir data/annotations/mvs/full_trf_gpu/chapters \
    --out-dir data/renders/mvs_piper_book \
    --tmp-dir data/tmp/mvs_piper_book \
    --voice en_US-libritts-high \
    --engine-workers '{"piper":2}' \
    --workers piper=2 \
    --crossfade-ms 120 \
    --lufs -18 \
    --resume

Note: This uses simple narration for all paragraphs. You can extend to per-speaker
styling later.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def build_script(chapter_json: Path, out_script: Path, engine: str, voice: str, pause_ms: int) -> int:
    data = json.loads(chapter_json.read_text(encoding="utf-8"))
    paras = data.get("paragraphs") or []
    items: list[dict[str, object]] = []
    for p in paras:
        t = (p or "").strip()
        if not t:
            continue
        items.append(
            {
                "text": t,
                "speaker": "narrator",
                "engine": engine,
                "voice": voice,
                "refs": [],
                "pause_ms": pause_ms,
                "style": "neutral",
            }
        )
    script = {
        "index": int(data.get("chapter_index") or 0),
        "title": data.get("title") or data.get("display_title") or "Chapter",
        "items": items,
    }
    out_script.parent.mkdir(parents=True, exist_ok=True)
    out_script.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(items)


essential = ["--engine-workers", "--workers", "--crossfade-ms", "--lufs"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--tmp-dir", type=Path, required=True)
    ap.add_argument("--engine", type=str, default="piper")
    ap.add_argument("--voice", type=str, default="en_US-libritts-high")
    ap.add_argument("--pause-ms", type=int, default=120)
    ap.add_argument("--engine-workers", type=str, default='{"piper":2}')
    ap.add_argument("--workers", type=str, default="piper=2")
    ap.add_argument("--crossfade-ms", type=int, default=120)
    ap.add_argument("--lufs", type=float, default=-18.0)
    ap.add_argument("--peak", type=float, default=-3.0)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)

    chapters = sorted([p for p in args.chapters_dir.glob("ch_*.json")])
    if not chapters:
        print(f"No chapters found in {args.chapters_dir}")
        return 1

    # Ensure base dirs
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.tmp_dir.mkdir(parents=True, exist_ok=True)

    for ch in chapters:
        # Prepare script path and target outputs
        with ch.open("r", encoding="utf-8") as f:
            data = json.load(f)
        idx = int(data.get("chapter_index") or 0)
        out_script = args.tmp_dir / "scripts" / f"ch_{idx:04d}.script.json"
        out_ch_wav = args.out_dir / "chapters" / f"ch_{idx:03d}.wav"
        out_ch_qc = args.out_dir / "qc" / f"ch_{idx:03d}.qc.json"

        # Skip if resume requested and outputs exist
        if args.resume and out_ch_wav.exists() and out_ch_qc.exists():
            print(f"[skip] ch_{idx:04d} already rendered")
            continue

        n_items = build_script(ch, out_script, args.engine, args.voice, args.pause_ms)
        if n_items == 0:
            print(f"[warn] ch_{idx:04d} has no items, skipping")
            continue

        cmd = [
            "python",
            "-m",
            "abm.audio.render_chapter",
            "--script",
            str(out_script),
            "--out-dir",
            str(args.out_dir),
            "--tmp-dir",
            str(args.tmp_dir),
            "--engine-workers",
            args.engine_workers,
            "--workers",
            args.workers,
            "--crossfade-ms",
            str(args.crossfade_ms),
            "--lufs",
            str(args.lufs),
            "--peak",
            str(args.peak),
            "--no-save-mp3",
            "--show-progress",
        ]
        env = os.environ.copy()
        print(f"[run] ch_{idx:04d} with {n_items} items")
        proc = subprocess.run(cmd, env=env)
        if proc.returncode != 0:
            print(f"[error] render failed for ch_{idx:04d} (rc={proc.returncode})")
            return proc.returncode

    print("All chapters rendered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
