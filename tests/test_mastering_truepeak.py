import numpy as np
import pytest

from abm.audio.mastering import master, measure_loudness, measure_true_peak

pytest.importorskip("scipy")


def test_measure_true_peak_exceeds_sample_peak():
    sr = 48000
    t = np.linspace(0, 0.01, int(sr * 0.01), endpoint=False)
    y = 0.99 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
    sample_peak = 20 * np.log10(np.max(np.abs(y)))
    tp = measure_true_peak(y, sr, oversample=8)
    assert tp >= sample_peak


def test_master_true_peak_ceiling():
    sr = 48000
    t = np.linspace(0, 0.01, int(sr * 0.01), endpoint=False)
    y = 0.99 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
    loud = measure_loudness(y, sr)
    y_out = master(
        y,
        sr,
        target_lufs=loud,
        peak_dbfs=0.0,
        head_ms=0,
        tail_ms=0,
        enable_true_peak=True,
        true_peak_ceiling_dbfs=-1.0,
        true_peak_oversample=8,
    )
    tp = measure_true_peak(y_out, sr, oversample=8)
    assert tp <= -0.9
