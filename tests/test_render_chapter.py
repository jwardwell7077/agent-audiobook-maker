import json
from pathlib import Path

import numpy as np
import soundfile as sf

from abm.audio.engine_registry import EngineRegistry
from abm.audio.render_chapter import main as render_main
from abm.audio.tts_base import TTSAdapter, TTSTask


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


def test_render_chapter_end_to_end(tmp_path):
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
    argv = [
        "--script",
        str(script_path),
        "--out-dir",
        str(out_dir),
        "--tmp-dir",
        str(tmp_dir),
        "--engine-workers",
        '{"dummy":1}',
        "--no-show-progress",
    ]
    render_main(argv)

    wav_path = out_dir / "chapters" / "ch_000.wav"
    qc_path = out_dir / "qc" / "ch_000.qc.json"
    manifest_path = out_dir / "manifests" / "book_manifest.json"
    assert wav_path.exists()
    assert qc_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["chapters"][0]["wav_path"] == "chapters/ch_000.wav"
    assert manifest["chapters"][0]["duration_s"] > 0
    assert isinstance(manifest["chapters"][0]["integrated_lufs"], float)

    EngineRegistry.unregister("dummy")
