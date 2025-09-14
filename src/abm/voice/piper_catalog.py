"""Catalog installed Piper voices.

This utility scans common Piper voice locations (or a provided directory) for
voice model files and associated metadata, then prints a concise inventory.

Usage:
    python -m abm.voice.piper_catalog --voices-dir ~/.local/share/piper/voices --json

Outputs either JSON or a simple table to stdout. No network access required.
"""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PiperVoice:
    """Simple description of a Piper voice installation."""

    id: str  # e.g., "en_US-ryan-high"
    model_path: Path
    config_path: Path | None
    language: str | None = None
    quality: str | None = None
    speaker: str | None = None
    sample_rate_hz: int | None = None


def _candidate_dirs(override: Path | None = None) -> list[Path]:
    if override is not None:
        return [override]
    env = os.environ.get("ABM_PIPER_VOICES_DIR")
    if env:
        return [Path(env)]
    return [
        Path.cwd() / "voices",
        Path.home() / ".local/share/piper/voices",
        Path("/usr/share/piper/voices"),
        Path("/usr/local/share/piper/voices"),
    ]


def _iter_voice_models(dirs: Iterable[Path]) -> Iterable[Path]:
    for d in dirs:
        if not d.exists():
            continue
        # Prefer voice models at top-level folders; but include nested too.
        yield from d.rglob("*.onnx*")


def _load_config(meta_path: Path) -> dict[str, Any] | None:
    try:
        data: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return None


def discover_piper_voices(voices_dir: Path | None = None) -> list[PiperVoice]:
    """Return a list of discovered Piper voices.

    We consider a voice defined by a model file ("*.onnx" or compressed) and
    optionally a matching JSON config (same stem with ".json").
    """

    roots = _candidate_dirs(voices_dir)
    out: list[PiperVoice] = []
    seen: set[str] = set()
    for model in _iter_voice_models(roots):
        # model name may include directory separators; voice id is last segment
        vid = model.stem
        # normalize common layout: .../en_US-ryan-high/en_US-ryan-high.onnx
        if model.parent.name and model.parent.joinpath(model.parent.name + ".onnx").exists():
            vid = model.parent.name
        # de-duplicate by id; prefer first seen
        if vid in seen:
            continue
        seen.add(vid)
        cfg_path = model.with_suffix("").with_suffix(".json")
        cfg = _load_config(cfg_path) if cfg_path.exists() else None
        lang = None
        quality = None
        sample_rate = None
        speaker = None
        if cfg:
            # piper voice config convention (may vary slightly across builds)
            espeak = cfg.get("espeak")
            if isinstance(espeak, dict):
                v = espeak.get("voice")
                lang = str(v) if v is not None else None
            else:
                val = cfg.get("language")
                lang = str(val) if val is not None else None

            q = cfg.get("quality") or cfg.get("quality_description")
            quality = str(q) if q is not None else None

            sr_val = cfg.get("sample_rate")
            if isinstance(sr_val, int | float):
                sample_rate = int(sr_val)
            else:
                sample_rate = None

            spk = cfg.get("speaker") or cfg.get("speaker_id")
            speaker = str(spk) if spk is not None else None
        out.append(
            PiperVoice(
                id=vid,
                model_path=model,
                config_path=cfg_path if cfg_path.exists() else None,
                language=lang,
                quality=quality,
                speaker=speaker,
                sample_rate_hz=sample_rate,
            )
        )
    return sorted(out, key=lambda v: v.id)


def main(argv: list[str] | None = None) -> int:
    p = ArgumentParser(prog="piper_catalog", description="List installed Piper voices")
    p.add_argument("--voices-dir", type=Path)
    p.add_argument("--json", action="store_true", help="Print JSON output")
    ns = p.parse_args(argv)

    voices = discover_piper_voices(ns.voices_dir)
    if ns.json:
        print(json.dumps([asdict(v) for v in voices], indent=2, default=str))
        return 0
    if not voices:
        print("No Piper voices found. Try --voices-dir or set ABM_PIPER_VOICES_DIR.")
        return 2
    # Text table
    colw = max(len(v.id) for v in voices)
    print(f"Found {len(voices)} voices:\n")
    print(f"{'VOICE ID'.ljust(colw)}  LANGUAGE   QUALITY   SR")
    print("-" * (colw + 26))
    for v in voices:
        sr = str(v.sample_rate_hz) if v.sample_rate_hz else "-"
        lang = v.language or "-"
        qual = v.quality or "-"
        print(f"{v.id.ljust(colw)}  {lang:<9}  {qual:<8}  {sr}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
