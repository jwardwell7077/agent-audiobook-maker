"""Render a chapter plan to audio using local TTS engines."""

from __future__ import annotations

import argparse
import json
import shutil
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from abm.audio.concat import equal_power_crossfade, micro_fade
from abm.audio.qc import duration_s, measure_lufs, peak_dbfs, write_qc_json
from abm.voice.cache import cache_path, make_cache_key
from abm.voice.engines import PiperEngine, XTTSEngine, ParlerEngine, ParlerConfig

__all__ = ["render_chapter", "main"]


_ENGINE_CACHE: dict[tuple[Any, ...], Any] = {}


def _load_engine(
    name: str,
    *,
    sample_rate: int | None = None,
    parler_model: str | None = None,
    parler_dtype: str = "auto",
) -> Any:
    key = (name, sample_rate, parler_model, parler_dtype)
    if key in _ENGINE_CACHE:
        return _ENGINE_CACHE[key]
    if name == "piper":
        eng = PiperEngine(sample_rate=sample_rate, use_subprocess=True)
    elif name == "xtts":
        eng = XTTSEngine(allow_stub=True, sample_rate=sample_rate or 48000)
    elif name == "parler":
        cfg = ParlerConfig(model_name=parler_model or ParlerConfig.model_name, dtype=parler_dtype)
        eng = ParlerEngine(cfg=cfg)
    else:
        raise KeyError(f"unknown engine {name}")
    _ENGINE_CACHE[key] = eng
    return eng


def _synth_segment(
    seg: dict[str, Any],
    sr: int,
    cache_dir: Path,
    tmp_dir: Path,
    *,
    parler_model: str,
    parler_dtype: str,
    parler_seed: int | None,
) -> np.ndarray:
    payload = {
        "engine": seg["engine"],
        "voice": seg["voice"],
        "text": seg["text"],
        "style": seg.get("style", {}),
        "sr": sr,
    }
    desc = seg.get("description") or ""
    seed = seg.get("seed", parler_seed)
    if seg["engine"] == "parler":
        payload.update(
            {
                "model": parler_model,
                "seed": seed,
                "desc": hashlib.sha256(desc.encode("utf-8")).hexdigest(),
            }
        )
    key = make_cache_key(payload)
    cache_fp = cache_path(cache_dir, seg["engine"], seg["voice"], key)
    if cache_fp.exists():
        y, _ = sf.read(cache_fp, dtype="float32")
        return y
    engine = _load_engine(
        seg["engine"],
        sample_rate=sr,
        parler_model=parler_model,
        parler_dtype=parler_dtype,
    )
    if seg["engine"] == "parler":
        y = engine.synthesize(
            seg["text"],
            seg["voice"],
            description=desc,
            seed=seed,
            style=seg.get("style", {}),
        )
    else:
        y = engine.synthesize(seg["text"], seg["voice"], seg.get("style", {}))
    if np.max(np.abs(y)) > 1.0:
        raise RuntimeError("audio clipping detected")
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
    parler_model: str = "parler-tts/parler-tts-mini-v1",
    parler_dtype: str = "auto",
    parler_seed: int | None = None,
) -> Path:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    sr = int(plan.get("sample_rate", 48000))
    crossfade_ms = int(plan.get("crossfade_ms", 0))
    if out_wav.exists() and not force:
        return out_wav
    segments = plan.get("segments", [])
    audio: list[np.ndarray] = []
    for seg in segments:
        y = _synth_segment(
            seg,
            sr,
            cache_dir,
            tmp_dir,
            parler_model=parler_model,
            parler_dtype=parler_dtype,
            parler_seed=parler_seed,
        )
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
    parser.add_argument("--parler-model", type=str, default="parler-tts/parler-tts-mini-v1")
    parser.add_argument("--parler-dtype", type=str, default="auto")
    parser.add_argument("--parler-seed", type=int, default=None)
    args = parser.parse_args(argv)
    render_chapter(
        args.chapter_plan,
        args.out_wav,
        args.cache_dir,
        args.tmp_dir,
        force=args.force,
        parler_model=args.parler_model,
        parler_dtype=args.parler_dtype,
        parler_seed=args.parler_seed,
    )
