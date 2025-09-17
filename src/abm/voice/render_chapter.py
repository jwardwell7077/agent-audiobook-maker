"""Render a chapter plan to audio using local TTS engines."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from abm.audio.concat import equal_power_crossfade, micro_fade
from abm.audio.qc import duration_s, measure_lufs, peak_dbfs, write_qc_json
from abm.voice.cache import cache_path, make_cache_key
from abm.voice.engines import ParlerConfig, ParlerEngine, PiperEngine, XTTSEngine

__all__ = ["render_chapter", "main"]


_ENGINE_CACHE: dict[tuple[Any, ...], Any] = {}
_ENGINE_CACHE_PID = os.getpid()


def _load_engine(
    name: str,
    *,
    sample_rate: int | None = None,
    parler_model: str | None = None,
    parler_dtype: str = "auto",
) -> Any:
    global _ENGINE_CACHE_PID
    pid = os.getpid()
    if pid != _ENGINE_CACHE_PID:
        _ENGINE_CACHE.clear()
        _ENGINE_CACHE_PID = pid
    key = (name, sample_rate, parler_model, parler_dtype)
    if key in _ENGINE_CACHE:
        return _ENGINE_CACHE[key]
    if name == "piper":
        eng = PiperEngine(sample_rate=sample_rate, use_subprocess=True)
    elif name == "xtts":
        eng = XTTSEngine(allow_stub=True, sample_rate=sample_rate or 48000)
    elif name == "parler":
        default_cfg = ParlerConfig()
        cfg = ParlerConfig(
            model_name=parler_model or default_cfg.model_name,
            dtype=parler_dtype,
        )
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
    engine_name: str,
    parler_model: str,
    parler_dtype: str,
    parler_seed: int | None,
) -> np.ndarray:
    payload = {
        "engine": engine_name,
        "voice": seg["voice"],
        "text": seg["text"],
        "style": seg.get("style", {}),
        "sr": sr,
    }
    desc = seg.get("description") or ""
    seed = seg.get("seed", parler_seed)
    desc_hash: str | None = None
    if engine_name == "parler":
        desc_hash = hashlib.sha256(desc.encode("utf-8")).hexdigest()
        payload.update(
            {
                "model_name": parler_model,
                "seed": seed,
                "description_sha": desc_hash,
            }
        )
    key = make_cache_key(payload)
    cache_fp = cache_path(cache_dir, engine_name, seg["voice"], key)
    if cache_fp.exists():
        y, _ = sf.read(cache_fp, dtype="float32")
        return y
    engine = _load_engine(
        engine_name,
        sample_rate=sr,
        parler_model=parler_model,
        parler_dtype=parler_dtype,
    )
    if engine_name == "parler":
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
    prefer_engine: str | None = None,
    add_pause_ms: int = 0,
) -> Path:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    sr = int(plan.get("sample_rate", 48000))
    crossfade_ms = int(plan.get("crossfade_ms", 0))
    if out_wav.exists() and not force:
        return out_wav
    segments = plan.get("segments", [])
    audio: list[np.ndarray] = []
    pauses: list[int] = []  # pause after each segment (ms); length == len(audio)
    utterances: list[dict[str, Any]] = []
    for seg in segments:
        engine_name = seg.get("engine") or prefer_engine or "piper"
        seg.setdefault("engine", engine_name)
        y = _synth_segment(
            seg,
            sr,
            cache_dir,
            tmp_dir,
            engine_name=engine_name,
            parler_model=parler_model,
            parler_dtype=parler_dtype,
            parler_seed=parler_seed,
        )
        y = micro_fade(y, sr)
        audio.append(y)
        # record the requested pause after this spoken segment
        pause_ms = int(seg.get("pause_ms", 0) or 0) + int(add_pause_ms or 0)
        pauses.append(max(0, pause_ms))
        # track utterance metadata for QC
        if engine_name == "parler":
            desc = seg.get("description") or ""
            desc_hash = hashlib.sha256(desc.encode("utf-8")).hexdigest()
            utterances.append(
                {
                    "id": seg.get("id"),
                    "engine": "parler",
                    "model": parler_model,
                    "voice": seg["voice"],
                    "seed": seg.get("seed", parler_seed),
                    "description_sha": desc_hash,
                    "text": seg["text"],
                }
            )
        else:
            utterances.append(
                {
                    "id": seg.get("id"),
                    "engine": engine_name,
                    "voice": seg["voice"],
                    "text": seg["text"],
                }
            )
    if not audio:
        return out_wav
    mix = audio[0]
    for idx, y in enumerate(audio[1:], start=1):
        # If a pause follows the previous segment, insert it and disable crossfade for this join
        p_ms = int(pauses[idx - 1] if idx - 1 < len(pauses) else 0)
        if p_ms > 0:
            n_sil = int(sr * (p_ms / 1000.0))
            if n_sil > 0:
                mix = np.concatenate([mix, np.zeros(n_sil, dtype=np.float32)]).astype(np.float32)
            cf_ms = 0
        else:
            cf_ms = crossfade_ms
        mix = equal_power_crossfade(mix, y, sr, cf_ms)
    # Optional debug: print total planned pauses and segments if requested
    if os.getenv("ABM_DEBUG_PAUSES"):
        total_pause_ms = int(sum(pauses[:-1]) if pauses else 0)
        print(f"[render_chapter] segments={len(audio)} total_pause_ms={total_pause_ms}")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out_wav, mix, sr)
    qc_path = out_wav.with_suffix(".qc.json")
    engines_used = sorted({meta["engine"] for meta in utterances})
    voices_used = sorted({meta["voice"] for meta in utterances if "voice" in meta})
    model_used = parler_model if "parler" in engines_used else None
    write_qc_json(
        qc_path,
        lufs=measure_lufs(mix, sr),
        peak_dbfs=peak_dbfs(mix),
        duration_s=duration_s(mix, sr),
        segments=len(audio),
        engines=engines_used,
        voices=voices_used,
        model=model_used,
        utterances=utterances,
    )
    return out_wav


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-plan", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--tmp-dir", type=Path, required=True)
    parser.add_argument("--out-wav", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--prefer-engine",
        type=str,
        default=None,
        help="Prefer this engine when segments omit an engine (default: plan value)",
    )
    parser.add_argument("--parler-model", type=str, default="parler-tts/parler-tts-mini-v1")
    parser.add_argument("--parler-dtype", type=str, default="auto")
    parser.add_argument(
        "--parler-seed",
        type=int,
        default=None,
        help="Default seed for Parler (renders are deterministic when a seed is set)",
    )
    parser.add_argument(
        "--add-pause-ms",
        type=int,
        default=0,
        help="Add this many milliseconds of extra silence after every segment",
    )
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
        prefer_engine=args.prefer_engine,
        add_pause_ms=args.add_pause_ms,
    )
