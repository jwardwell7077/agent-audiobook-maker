from pathlib import Path

import numpy as np
import soundfile as sf

from abm.audio.tts_base import TTSAdapter, TTSTask
from abm.audio.tts_manager import TTSManager


class DummyAdapter(TTSAdapter):
    def preload(self) -> None:  # pragma: no cover - trivial
        pass

    def synth(self, task: TTSTask) -> Path:
        sr = 16000
        t = np.linspace(0, 0.15, int(sr * 0.15), endpoint=False)
        y = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        task.out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(task.out_path, y, sr, subtype="PCM_16")
        return task.out_path


def make_tasks(out_dir: Path) -> list[TTSTask]:
    return [
        TTSTask(
            text=f"hello {i}",
            speaker="narrator",
            engine="dummy",
            voice=None,
            profile_id=None,
            refs=[],
            out_path=out_dir / f"{i}.wav",
            pause_ms=0,
            style="",
        )
        for i in range(3)
    ]


def test_render_batch_uses_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    adapter = DummyAdapter()
    manager = TTSManager(adapter, cache_dir=cache_dir, show_progress=False)

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    tasks1 = make_tasks(out1)
    manager.render_batch(tasks1)
    for t in tasks1:
        assert t.out_path.exists()

    tasks2 = make_tasks(out2)
    calls = {"n": 0}

    def fake_synth(task: TTSTask) -> Path:
        calls["n"] += 1
        return task.out_path

    monkeypatch.setattr(adapter, "synth", fake_synth)
    manager.render_batch(tasks2)
    assert calls["n"] == 0
    for t1, t2 in zip(tasks1, tasks2, strict=False):
        assert t2.out_path.exists()
        assert t1.out_path.read_bytes() == t2.out_path.read_bytes()
