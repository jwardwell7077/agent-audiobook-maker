from pathlib import Path

import numpy as np
import soundfile as sf

from abm.audio.assembly import assemble
from abm.audio.mastering import master, measure_loudness
from abm.audio.qc_report import qc_report


def write_sine(path: Path, freq: float, dur: float, sr: int = 16000) -> None:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    y = np.sin(2 * np.pi * freq * t).astype(np.float32)
    sf.write(path, y, sr, subtype="PCM_16")


def test_assemble_master_qc(tmp_path):
    p1 = tmp_path / "a.wav"
    p2 = tmp_path / "b.wav"
    sr = 16000
    write_sine(p1, 440, 0.3, sr)
    write_sine(p2, 660, 0.2, sr)

    y, sr_out = assemble([p1, p2], pauses_ms=[100, 150], crossfade_ms=20)
    assert sr_out == sr
    assert np.abs(y).max() <= 1.0

    expected_dur = 0.3 + 0.1 + 0.2 + 0.15 - 0.02
    assert abs(len(y) / sr - expected_dur) / expected_dur < 0.01

    loud_before = measure_loudness(y, sr)
    y_master = master(y, sr, target_lufs=-18.0, peak_dbfs=-3.0)
    loud_after = measure_loudness(y_master, sr)
    assert abs(loud_after + 18.0) < abs(loud_before + 18.0)
    peak_dbfs = 20 * np.log10(np.max(np.abs(y_master)) + 1e-9)
    assert peak_dbfs <= -3.0 + 1e-3

    report = qc_report(y_master, sr)
    for key in [
        "duration_s",
        "integrated_lufs",
        "peak_dbfs",
        "rms_dbfs",
        "approx_noise_floor_dbfs",
    ]:
        assert key in report
    assert isinstance(report["duration_s"], float)
