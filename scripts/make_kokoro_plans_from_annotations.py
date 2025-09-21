#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

"""
Generate Kokoro-compatible chapter plans from annotation chapter JSONs.

Inputs
- --chapters-dir: Directory containing ch_*.json annotation files (e.g., data/ann/mvs/chapters)
- --out-dir: Destination directory for Kokoro plans (e.g., tmp/data/ann/mvs/plans)
- --narrator: Default speaker name to attribute paragraphs to (used for voice mapping)
- --pause-ms: Pause to insert after each paragraph/segment
- --overwrite: Overwrite existing plan files (default: False)

Plan schema (subset used by abm.voice.render_chapter):
{
    "crossfade_ms": 0,
    "segments": [
        {
            "id": "{chapter:03d}-{seg:05d}",
            "speaker": "Narrator",
            "kind": "narration",
            "text": "...",
            "pause_ms": 120,
            "engine": "kokoro",
            "voice": "af_bella",
            "style": {"pace": 1.0}
        }
    ]
}
"""

KOKORO_MAP_JSON = Path("seed_pack/kokoro_characters.json")


def _load_kokoro_map() -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    try:
        if KOKORO_MAP_JSON.exists():
            data = json.loads(KOKORO_MAP_JSON.read_text(encoding="utf-8"))
            for row in data:
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                mapping[name] = {
                    "voice_id": row.get("voice_id"),
                    "speed": row.get("speed"),
                }
    except Exception:
        mapping = {}
    return mapping


_KOKORO_RE = re.compile(r"^[ab][fm]_[a-z]+$")


def _resolve_voice_for_speaker(speaker: str, default_voice: str = "af_bella") -> tuple[str, float | None]:
    km = _load_kokoro_map()
    row = km.get(speaker or "")
    if row and row.get("voice_id"):
        vid = str(row["voice_id"]).strip()
        spd = row.get("speed")
        try:
            pace = float(spd) if spd is not None else None
        except Exception:
            pace = None
        return vid, pace
    return default_voice, None


def build_plan_from_paragraphs(chapter_json: Path, narrator: str, pause_ms: int) -> dict[str, Any]:
    data = json.loads(chapter_json.read_text(encoding="utf-8"))
    idx = int(data.get("chapter_index") or 0)
    title = data.get("title") or data.get("display_title") or "Chapter"
    paragraphs = data.get("paragraphs") or []

    voice_id, pace = _resolve_voice_for_speaker(narrator)
    style: dict[str, Any] = {}
    if pace is not None:
        style["pace"] = float(pace)

    segments: list[dict[str, Any]] = []
    for si, p in enumerate(paragraphs, start=1):
        t = (p or "").strip()
        if not t:
            continue
        segments.append(
            {
                "id": f"{idx:03d}-{si:05d}",
                "speaker": narrator,
                "kind": "narration",
                "text": t,
                "pause_ms": int(pause_ms),
                "engine": "kokoro",
                "voice": voice_id,
                "style": style.copy(),
            }
        )

    return {
        "chapter_index": idx,
        "title": title,
        "crossfade_ms": 0,
        "segments": segments,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chapters-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--narrator", type=str, default="Narrator")
    ap.add_argument("--pause-ms", type=int, default=120)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    ch_files = sorted(args.chapters_dir.glob("ch_*.json"))
    if not ch_files:
        print(f"No chapters found in {args.chapters_dir}")
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    for ch in ch_files:
        dst = args.out_dir / ch.name
        if dst.exists() and not args.overwrite:
            skipped += 1
            continue
        plan = build_plan_from_paragraphs(ch, args.narrator, args.pause_ms)
        dst.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1
    print(f"Wrote {written} plans, skipped {skipped} (already exist) → {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
