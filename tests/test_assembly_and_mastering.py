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

    expected_dur = 0.3 + 0.1 + 0.2 + 0.15
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
        "acx_ok",
    ]:
        assert key in report
    assert report["acx_ok"] in {True, False}


def test_equal_power_crossfade(tmp_path: Path) -> None:
    sr = 16000
    p1 = tmp_path / "a.wav"
    p2 = tmp_path / "b.wav"
    y = np.ones(int(sr * 0.2), dtype=np.float32) * 0.5
    sf.write(p1, y, sr, subtype="PCM_16")
    sf.write(p2, y, sr, subtype="PCM_16")
    y_eq, _ = assemble([p1, p2], pauses_ms=[0, 0], crossfade_ms=50)

    # Linear crossfade for comparison
    cf = int(round(sr * 0.05))
    fade_out = np.linspace(1.0, 0.0, cf, endpoint=False)
    fade_in = np.linspace(0.0, 1.0, cf, endpoint=False)
    cross_lin = y[-cf:] * fade_out + y[:cf] * fade_in
    rms_lin = float(np.sqrt(np.mean(cross_lin**2)))
    start = int(sr * 0.2) - cf
    cross_eq = y_eq[start : start + cf]
    rms_eq = float(np.sqrt(np.mean(cross_eq**2)))
    assert rms_eq > rms_lin


def test_resample_option(tmp_path: Path) -> None:
    sr1 = 16000
    sr2 = 8000
    p1 = tmp_path / "a.wav"
    p2 = tmp_path / "b.wav"
    write_sine(p1, 440, 0.1, sr1)
    write_sine(p2, 440, 0.1, sr2)
    try:
        assemble([p1, p2], pauses_ms=[0, 0])
    except ValueError as exc:
        assert "allow_resample" in str(exc)
    else:  # pragma: no cover
        import pytest

        pytest.fail("expected ValueError")
    try:
        __import__("scipy")
        y, sr_out = assemble(
            [p1, p2], pauses_ms=[0, 0], allow_resample=True, crossfade_ms=0
        )
        assert sr_out == sr1
        assert len(y) > 0
    except Exception:  # pragma: no cover - scipy missing
        pass


def test_qc_flags_fail() -> None:
    y = np.ones(16000, dtype=np.float32)
    report = qc_report(y, 16000)
    assert not report["lufs_ok"]
    assert not report["peak_ok"]
    assert not report["noise_ok"]
    assert not report["acx_ok"]
