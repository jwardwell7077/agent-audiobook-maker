"""Render a chapter plan to audio using local TTS engines."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from abm.audio.concat import equal_power_crossfade, micro_fade
from abm.audio.qc import duration_s, measure_lufs, peak_dbfs, write_qc_json
from abm.voice.cache import cache_path, make_cache_key
from abm.voice.engines import PiperEngine, XTTSEngine

__all__ = ["render_chapter", "main"]


def _load_engine(name: str) -> Any:
    if name == "piper":
        return PiperEngine()
    if name == "xtts":
        return XTTSEngine(allow_stub=True)
    raise KeyError(f"unknown engine {name}")


def _synth_segment(
    seg: dict[str, Any], sr: int, cache_dir: Path, tmp_dir: Path
) -> np.ndarray:
    payload = {
        "engine": seg["engine"],
        "voice": seg["voice"],
        "text": seg["text"],
        "style": seg.get("style", {}),
        "sr": sr,
    }
    key = make_cache_key(payload)
    cache_fp = cache_path(cache_dir, seg["engine"], seg["voice"], key)
    if cache_fp.exists():
        y, _ = sf.read(cache_fp, dtype="float32")
        return y
    engine = _load_engine(seg["engine"])
    y = engine.synthesize(seg["text"], seg["voice"], seg.get("style", {}))
    tmp_fp = tmp_dir / f"{seg['id']}.wav"
    tmp_fp.parent.mkdir(parents=True, exist_ok=True)
    sf.write(tmp_fp, y, sr)
    cache_fp.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(tmp_fp, cache_fp)
    return y


def render_chapter(
    plan_path: Path,
    out_wav: Path,
    cache_dir: Path,
    tmp_dir: Path,
    *,
    force: bool = False,
) -> Path:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    sr = int(plan.get("sample_rate", 48000))
    crossfade_ms = int(plan.get("crossfade_ms", 0))
    if out_wav.exists() and not force:
        return out_wav
    segments = plan.get("segments", [])
    audio: list[np.ndarray] = []
    for seg in segments:
        y = _synth_segment(seg, sr, cache_dir, tmp_dir)
        y = micro_fade(y, sr)
        audio.append(y)
    if not audio:
        return out_wav
    mix = audio[0]
    for y in audio[1:]:
        mix = equal_power_crossfade(mix, y, sr, crossfade_ms)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_wav, mix, sr)
    qc_path = out_wav.with_suffix(".qc.json")
    write_qc_json(
        qc_path,
        lufs=measure_lufs(mix, sr),
        peak_dbfs=peak_dbfs(mix),
        duration_s=duration_s(mix, sr),
        segments=len(audio),
    )
    return out_wav


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-plan", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--tmp-dir", type=Path, required=True)
    parser.add_argument("--out-wav", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    render_chapter(
        args.chapter_plan, args.out_wav, args.cache_dir, args.tmp_dir, force=args.force
    )
