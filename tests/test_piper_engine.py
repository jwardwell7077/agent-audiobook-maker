import subprocess

import numpy as np
import soundfile as sf

from abm.voice.engines.piper_engine import PiperEngine


def test_piper_engine_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "abm.voice.engines.piper_engine.shutil.which", lambda name: "piper"
    )

    def fake_run(cmd, input=None, capture_output=True):
        out_path = cmd[cmd.index("-f") + 1]
        t = np.linspace(0, 0.1, int(48000 * 0.1), endpoint=False)
        y = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        sf.write(out_path, y, 48000)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr("abm.voice.engines.piper_engine.subprocess.run", fake_run)
    engine = PiperEngine(use_subprocess=True)
    y = engine.synthesize("hi", "voice")
    assert y.dtype == np.float32
    assert y.shape[0] == int(48000 * 0.1)


def test_piper_engine_tone(monkeypatch):
    monkeypatch.setattr(
        "abm.voice.engines.piper_engine.shutil.which", lambda name: None
    )
    engine = PiperEngine()
    y = engine.synthesize("hi", "voice")
    assert y.dtype == np.float32
    assert y.ndim == 1
    assert y.shape[0] > 0
