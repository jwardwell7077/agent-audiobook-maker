"""Simple mastering utilities for audiobook audio."""

from __future__ import annotations

import numpy as np
import pyloudnorm as pyln

__all__ = [
    "measure_loudness",
    "limit_peaks",
    "add_head_tail_silence",
    "master",
]


def measure_loudness(y: np.ndarray, sr: int) -> float:
    """Return integrated loudness (LUFS)."""

    try:
        meter = pyln.Meter(sr)
        loud = float(meter.integrated_loudness(y))
    except Exception:
        return float("-inf")
    if np.isinf(loud):
        return float("-inf")
    return loud


def limit_peaks(y: np.ndarray, peak_dbfs: float = -3.0) -> np.ndarray:
    """Limit waveform peaks to the given dBFS value."""

    target_amp = 10 ** (peak_dbfs / 20)
    peak = float(np.max(np.abs(y)) + 1e-9)
    if peak > target_amp:
        y = y * (target_amp / peak)
    return y.astype(np.float32)


def add_head_tail_silence(
    y: np.ndarray, sr: int, head_ms: int, tail_ms: int
) -> np.ndarray:
    """Pad audio with silence before and after."""

    from abm.audio.assembly import silence

    head = silence(head_ms, sr)
    tail = silence(tail_ms, sr)
    return np.concatenate([head, y, tail]).astype(np.float32)


def master(
    y: np.ndarray,
    sr: int,
    *,
    target_lufs: float = -18.0,
    peak_dbfs: float = -3.0,
    head_ms: int = 700,
    tail_ms: int = 900,
) -> np.ndarray:
    """Master audio to target loudness and peak limits."""

    loud = measure_loudness(y, sr)
    if np.isfinite(loud):
        diff = target_lufs - loud
        if abs(diff) > 1.0:
            y = y * (10 ** (diff / 20))
    y = limit_peaks(y, peak_dbfs)
    y = add_head_tail_silence(y, sr, head_ms, tail_ms)
    return np.clip(y, -1.0, 1.0).astype(np.float32)
