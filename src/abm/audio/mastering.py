"""Simple mastering utilities for audiobook audio."""

from __future__ import annotations

import logging

import numpy as np
import pyloudnorm as pyln

try:  # Optional oversampling support
    from scipy.signal import resample_poly
except Exception:  # pragma: no cover - scipy is optional
    resample_poly = None  # type: ignore[assignment]

__all__ = [
    "measure_loudness",
    "measure_true_peak",
    "limit_peaks",
    "add_head_tail_silence",
    "master",
]


logger = logging.getLogger(__name__)


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


def measure_true_peak(y: np.ndarray, sr: int, *, oversample: int = 4) -> float:
    """Estimate true peak in dBFS via optional oversampling.

    Args:
        y: Mono audio in float32 range ``[-1, 1]``.
        sr: Sample rate in Hz.
        oversample: Oversampling factor (>=2 uses ``scipy``; <2 uses sample peak).

    Returns:
        True-peak value in dBFS. ``-inf`` if the signal is silent.

    Notes:
        If :mod:`scipy` is unavailable, the function falls back to a simple
        sample peak measurement without oversampling.
    """

    if y.size == 0:
        return float("-inf")
    if oversample >= 2 and resample_poly is not None:
        try:
            y = resample_poly(y, oversample, 1)
        except Exception:  # pragma: no cover - rare resample errors
            logger.warning("resample_poly failed; falling back to sample peak")
    peak = float(np.max(np.abs(y)))
    if peak <= 0:
        return float("-inf")
    return 20 * np.log10(peak + 1e-12)


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
    enable_true_peak: bool = False,
    true_peak_ceiling_dbfs: float = -1.2,
    true_peak_oversample: int = 4,
) -> np.ndarray:
    """Master audio to target loudness and peak limits.

    Processing order: loudness match → peak limit → optional true-peak safety →
    head/tail silence. When ``enable_true_peak`` is ``True`` an additional
    global gain is applied to ensure the oversampled true peak does not exceed
    ``true_peak_ceiling_dbfs``.

    Args:
        y: Mono audio ``[-1, 1]``.
        sr: Sample rate in Hz.
        target_lufs: Desired integrated loudness.
        peak_dbfs: Sample-peak ceiling applied before true-peak safety.
        head_ms: Leading silence in milliseconds.
        tail_ms: Trailing silence in milliseconds.
        enable_true_peak: Whether to enforce a true-peak ceiling.
        true_peak_ceiling_dbfs: True-peak ceiling in dBFS.
        true_peak_oversample: Oversampling factor for true-peak measurement.

    Returns:
        The mastered waveform in float32.

    Notes:
        This function performs a simple protective gain and does not implement a
        look-ahead limiter.
    """

    loud = measure_loudness(y, sr)
    if np.isfinite(loud):
        diff = target_lufs - loud
        if abs(diff) > 1.0:
            y = y * (10 ** (diff / 20))

    y = limit_peaks(y, peak_dbfs)

    if enable_true_peak:
        tp = measure_true_peak(y, sr, oversample=true_peak_oversample)
        if np.isfinite(tp) and tp > true_peak_ceiling_dbfs:
            gain = 10 ** ((true_peak_ceiling_dbfs - tp) / 20)
            y = y * gain
        y = np.clip(y, -1.0, 1.0)

    y = add_head_tail_silence(y, sr, head_ms, tail_ms)
    return np.clip(y, -1.0, 1.0).astype(np.float32)
