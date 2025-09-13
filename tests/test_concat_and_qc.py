import json
from pathlib import Path

import numpy as np
import pytest

from abm.audio.concat import equal_power_crossfade, micro_fade
from abm.audio.qc import duration_s, measure_lufs, peak_dbfs, write_qc_json


def test_concat_and_fade_and_qc(tmp_path: Path) -> None:
    sr = 48000
    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    a = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    b = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    joined = equal_power_crossfade(a, b, sr, 50)
    expected_len = len(a) + len(b) - int(sr * 0.05)
    assert len(joined) == expected_len

    faded = micro_fade(a, sr)
    assert abs(faded[0]) < 1e-3
    assert abs(faded[-1]) < 1e-3

    lufs = measure_lufs(a, sr)
    peak = peak_dbfs(a)
    dur = duration_s(a, sr)
    out = tmp_path / "qc.json"
    write_qc_json(out, lufs=lufs, peak_dbfs=peak, duration_s=dur, segments=1)
    data = json.loads(out.read_text())
    assert data["segments"] == 1
    assert isinstance(data["lufs"], float)
    assert data["duration_s"] == pytest.approx(dur)
