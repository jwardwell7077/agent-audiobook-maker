"""Quality-control utilities for rendered audio."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from abm.audio.mastering import measure_loudness

__all__ = ["qc_report", "write_qc_json"]

_EPS = 1e-9


def qc_report(y: np.ndarray, sr: int) -> dict:
    """Compute basic QC metrics for an audio signal.

    The ``approx_noise_floor_dbfs`` metric uses the 10th percentile of the
    absolute amplitude as a rough estimate of the noise floor. ACX compliance
    flags are included: ``lufs_ok``, ``peak_ok``, ``noise_ok`` and ``acx_ok``.

    Args:
        y: Audio samples in the range ``[-1, 1]``.
        sr: Sample rate in Hz.

    Returns:
        Dictionary containing duration, level statistics and ACX flags.
    """

    duration_s = float(len(y) / sr)
    peak_dbfs = float(20 * np.log10(np.max(np.abs(y)) + _EPS))
    rms = float(np.sqrt(np.mean(y**2)))
    rms_dbfs = float(20 * np.log10(rms + _EPS))
    noise_floor = float(np.percentile(np.abs(y), 10))
    noise_dbfs = float(20 * np.log10(noise_floor + _EPS))
    lufs = measure_loudness(y, sr)
    lufs_ok = -23.0 <= lufs <= -18.0 if np.isfinite(lufs) else False
    peak_ok = peak_dbfs <= -3.0
    noise_ok = noise_dbfs <= -60.0
    return {
        "duration_s": duration_s,
        "integrated_lufs": lufs,
        "peak_dbfs": peak_dbfs,
        "rms_dbfs": rms_dbfs,
        "approx_noise_floor_dbfs": noise_dbfs,
        "lufs_ok": lufs_ok,
        "peak_ok": peak_ok,
        "noise_ok": noise_ok,
        "acx_ok": lufs_ok and peak_ok and noise_ok,
    }


def write_qc_json(report: dict, out_path: Path) -> None:
    """Write a QC report dictionary to JSON."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
