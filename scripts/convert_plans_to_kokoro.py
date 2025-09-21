#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

# Default inputs (can be overridden via CLI)
DEF_IN_DIR = Path("data/ann/mvs/plans")  # source legacy plans
DEF_OUT_DIR = Path("tmp/data/ann/mvs/plans")  # destination kokoro plans

# Optional casting sources
KOKORO_MAP_JSON = Path("seed_pack/kokoro_characters.json")
KOKORO_PROFILES_YML = Path("seed_pack/profiles.kokoro.yml")

# Heuristic: kokoro voice-id pattern
_KOKORO_RE = re.compile(r"^[ab][fm]_[a-z]+$")


def _load_kokoro_map() -> dict[str, dict[str, Any]]:
    # Prefer explicit kokoro_characters.json if present
    if KOKORO_MAP_JSON.exists():
        data = json.loads(KOKORO_MAP_JSON.read_text(encoding="utf-8"))
        m: dict[str, dict[str, Any]] = {}
        for row in data:
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            m[name] = {"voice_id": row.get("voice_id"), "speed": row.get("speed")}
        return m
    # Fallback: parse minimal speakers from the YAML if present (no YAML dep)
    if KOKORO_PROFILES_YML.exists():
        speakers: dict[str, dict[str, Any]] = {}
        current = None
        for line in KOKORO_PROFILES_YML.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            if not line.startswith(" ") and not line.startswith("\t") and ":" in line:
                # top-level keys, skip
                continue
            # naive parse: two-space indent speakers: "  Name:" then nested keys
            if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
                current = line.strip().rstrip(":")
                speakers[current] = {}
                continue
            if current and line.startswith("    ") and ":" in line:
                k, v = [x.strip() for x in line.strip().split(":", 1)]
                v = v.strip()
                if k == "voice":
                    speakers[current]["voice_id"] = v
        return speakers
    return {}


def _resolve_voice(speaker: str, seg_voice: str | None, km: dict[str, dict[str, Any]]) -> tuple[str, float | None]:
    voice = (seg_voice or "").strip()
    speed: float | None = None
    if _KOKORO_RE.match(voice):
        return voice, None
    row = km.get(speaker or "")
    if row and row.get("voice_id"):
        voice = str(row["voice_id"]).strip()
        spd = row.get("speed")
        try:
            speed = float(spd) if spd is not None else None
        except Exception:
            speed = None
    if not voice:
        voice = "af_bella"
    return voice, speed


def convert_one(src: Path, dst: Path, km: dict[str, dict[str, Any]]) -> None:
    plan = json.loads(src.read_text(encoding="utf-8"))
    segs = plan.get("segments", [])
    out = []
    for seg in segs:
        engine = "kokoro"
        speaker = seg.get("speaker")
        voice_id, spd = _resolve_voice(speaker, seg.get("voice"), km)
        style = seg.get("style") or {}
        # inject speed into style if not already present
        if spd is not None:
            if isinstance(style, dict):
                style = dict(style)
                style.setdefault("pace", spd)
            else:
                style = f"{style} pace={spd}"
        out.append(
            {
                "id": seg.get("id"),
                "speaker": speaker,
                "kind": seg.get("kind"),
                "text": seg.get("text"),
                "pause_ms": int(seg.get("pause_ms", 0) or 0),
                "engine": engine,
                "voice": voice_id,
                "style": style,
            }
        )
    plan["segments"] = out
    # Drop Parler-only items if present
    for k in ("description", "seed"):
        plan.pop(k, None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Convert legacy chapter plans to Kokoro-compatible plans")
    ap.add_argument("--in-dir", type=Path, default=DEF_IN_DIR, help="Source directory with legacy ch_*.json plans")
    ap.add_argument("--out-dir", type=Path, default=DEF_OUT_DIR, help="Destination directory for Kokoro plans")
    ap.add_argument("--pattern", type=str, default="ch_*.json", help="Glob pattern for plan files")
    args = ap.parse_args(argv)

    km = _load_kokoro_map()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.in_dir.glob(args.pattern))
    for src in files:
        dst = args.out_dir / src.name
        convert_one(src, dst, km)
    print(f"Wrote {len(files)} Kokoro plans → {args.out_dir}")


if __name__ == "__main__":
    main()
