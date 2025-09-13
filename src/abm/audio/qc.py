"""Quality-control helpers for rendered audio."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["measure_lufs", "peak_dbfs", "duration_s", "write_qc_json"]

logger = logging.getLogger(__name__)


def measure_lufs(y: np.ndarray, sr: int) -> float:
    """Return integrated loudness (LUFS).

    Uses :mod:`pyloudnorm` if available, otherwise returns ``nan`` and logs a
    warning.
    """

    try:  # pragma: no cover - optional dependency
        import pyloudnorm as pyln
    except Exception:  # pragma: no cover - missing dep
        logger.warning("pyloudnorm not available; returning NaN for LUFS")
        return float("nan")
    meter = pyln.Meter(sr)
    try:
        return float(meter.integrated_loudness(y))
    except Exception:  # pragma: no cover - rare
        return float("nan")


def peak_dbfs(y: np.ndarray) -> float:
    """Return sample peak in dBFS."""

    peak = float(np.max(np.abs(y)))
    if peak <= 0:
        return float("-inf")
    return 20 * np.log10(peak)


def duration_s(y: np.ndarray, sr: int) -> float:
    """Return duration of ``y`` in seconds."""

    return float(y.size) / float(sr)


def write_qc_json(
    path: Path, *, lufs: float, peak_dbfs: float, duration_s: float, segments: int
) -> None:
    """Write a JSON file with QC metrics."""

    data: dict[str, Any] = {
        "lufs": lufs,
        "peak_dbfs": peak_dbfs,
        "duration_s": duration_s,
        "segments": segments,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
