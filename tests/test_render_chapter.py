import json
from pathlib import Path

import numpy as np
import soundfile as sf

from abm.audio.engine_registry import EngineRegistry
from abm.audio.render_chapter import main as render_main
from abm.audio.tts_base import TTSAdapter, TTSTask
from abm.audio.tts_manager import TTSManager


class DummyAdapter(TTSAdapter):
    def preload(self) -> None:  # pragma: no cover - trivial
        pass

    def synth(self, task: TTSTask) -> Path:
        sr = 16000
        t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
        y = np.sin(2 * np.pi * 330 * t).astype(np.float32)
        task.out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(task.out_path, y, sr, subtype="PCM_16")
        return task.out_path


def test_render_chapter_end_to_end(tmp_path, monkeypatch):
    EngineRegistry.unregister("dummy")
    EngineRegistry.register("dummy", lambda **_: DummyAdapter())

    script = {
        "index": 0,
        "title": "Test",
        "items": [
            {
                "text": "Hello",
                "speaker": "narrator",
                "engine": "dummy",
                "refs": [],
                "pause_ms": 50,
            },
            {
                "text": "World",
                "speaker": "narrator",
                "engine": "dummy",
                "refs": [],
                "pause_ms": 50,
            },
        ],
    }
    script_path = tmp_path / "script.json"
    script_path.write_text(json.dumps(script))

    out_dir = tmp_path / "out"
    tmp_dir = tmp_path / "tmp"
    spans_dir = tmp_dir / "spans"
    spans_dir.mkdir(parents=True, exist_ok=True)
    # pre-create first span to test resume behaviour
    pre_path = spans_dir / "c000.wav"
    sr = 16000
    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    sf.write(pre_path, np.sin(2 * np.pi * 330 * t).astype(np.float32), sr)

    synth_calls = {"n": 0}
    orig_synth = DummyAdapter.synth

    def counting_synth(self, task: TTSTask) -> Path:
        synth_calls["n"] += 1
        return orig_synth(self, task)

    monkeypatch.setattr(DummyAdapter, "synth", counting_synth)

    captured_workers: list[int] = []
    orig_init = TTSManager.__init__

    def spy_init(self, adapter, max_workers=2, cache_dir=None, show_progress=True):
        captured_workers.append(max_workers)
        orig_init(self, adapter, max_workers, cache_dir, show_progress)

    monkeypatch.setattr(TTSManager, "__init__", spy_init)

    argv = [
        "--script",
        str(script_path),
        "--out-dir",
        str(out_dir),
        "--tmp-dir",
        str(tmp_dir),
        "--engine-workers",
        '{"dummy":2}',
        "--workers",
        "dummy=1",
        "--no-show-progress",
    ]
    render_main(argv)

    assert synth_calls["n"] == 1
    assert captured_workers[0] == 1

    wav_path = out_dir / "chapters" / "ch_000.wav"
    qc_path = out_dir / "qc" / "ch_000.qc.json"
    manifest_path = out_dir / "manifests" / "book_manifest.json"
    assert wav_path.exists()
    assert qc_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["chapters"][0]["wav_path"] == "chapters/ch_000.wav"
    assert manifest["chapters"][0]["duration_s"] > 0
    assert isinstance(manifest["chapters"][0]["integrated_lufs"], float)
    assert manifest["provenance"]["engine_workers"]["dummy"] == 1

    EngineRegistry.unregister("dummy")
