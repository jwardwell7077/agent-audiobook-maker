import json
from pathlib import Path

import numpy as np
import soundfile as sf

from abm.audio.album_norm import (
    apply_album_gain,
    collect_chapter_stats,
    compute_album_offset,
    write_album_manifest,
)
from abm.audio.engine_registry import EngineRegistry
from abm.audio.packaging import export_mp3, export_opus, write_chapter_cue
from abm.audio.render_book import main as render_book_main
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


def test_render_book_with_resume(tmp_path, monkeypatch):
    EngineRegistry.unregister("dummy")
    EngineRegistry.register("dummy", lambda **_: DummyAdapter())

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    for i in range(2):
        script = {
            "index": i,
            "title": f"Ch{i}",
            "items": [
                {
                    "text": "hi",
                    "speaker": "n",
                    "engine": "dummy",
                    "refs": [],
                }
            ],
        }
        (scripts_dir / f"ch_{i:03d}.synth.json").write_text(json.dumps(script))

    out_dir = tmp_path / "out"

    argv = [
        "--scripts",
        str(scripts_dir),
        "--out-dir",
        str(out_dir),
        "--engine-workers",
        '{"dummy":1}',
        "--no-show-progress",
    ]
    render_book_main(argv)

    calls = {"n": 0}

    def counting(self, task: TTSTask) -> Path:
        calls["n"] += 1
        return DummyAdapter.synth(self, task)

    monkeypatch.setattr(DummyAdapter, "synth", counting)

    argv_resume = argv + ["--resume"]
    render_book_main(argv_resume)

    assert calls["n"] == 0
    manifest_path = out_dir / "manifests" / "book_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["chapters"]) == 2

    EngineRegistry.unregister("dummy")


def test_album_normalization(tmp_path):
    sr = 16000
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    quiet = 0.1 * np.sin(2 * np.pi * 220 * t)
    loud = 0.8 * np.sin(2 * np.pi * 220 * t)
    wav0 = tmp_path / "ch_000.wav"
    wav1 = tmp_path / "ch_001.wav"
    sf.write(wav0, quiet, sr)
    sf.write(wav1, loud, sr)

    qc_dir = tmp_path / "qc"
    qc_dir.mkdir()
    qc0 = qc_dir / "ch_000.qc.json"
    qc1 = qc_dir / "ch_001.qc.json"
    qc0.write_text(
        json.dumps({"duration_s": 0.5, "integrated_lufs": -25.0, "peak_dbfs": -20})
    )
    qc1.write_text(
        json.dumps({"duration_s": 0.5, "integrated_lufs": -15.0, "peak_dbfs": -1})
    )

    manifest = {
        "chapters": [
            {"index": 0, "qc_path": f"qc/{qc0.name}", "wav_path": wav0.name},
            {"index": 1, "qc_path": f"qc/{qc1.name}", "wav_path": wav1.name},
        ]
    }
    manif_dir = tmp_path / "manifests"
    manif_dir.mkdir()
    manifest_path = manif_dir / "book_manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    stats = collect_chapter_stats(manifest_path)
    offset = compute_album_offset(stats, target_lufs=-18.0)
    out0 = tmp_path / "n0.wav"
    out1 = tmp_path / "n1.wav"
    apply_album_gain(wav0, out0, offset)
    apply_album_gain(wav1, out1, offset)
    y0, _ = sf.read(out0, dtype="float32")
    y1, _ = sf.read(out1, dtype="float32")
    assert np.max(np.abs(y0)) > np.max(np.abs(quiet))
    assert np.max(np.abs(y1)) <= 10 ** (-1.2 / 20) + 1e-4
    write_album_manifest(tmp_path / "album.json", offset)


def test_packaging_exports(tmp_path):
    sr = 16000
    t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
    y = np.sin(2 * np.pi * 440 * t)
    in_wav = tmp_path / "in.wav"
    sf.write(in_wav, y, sr)

    try:
        export_mp3(
            in_wav,
            tmp_path / "out.mp3",
            title="t",
            artist="a",
            album="b",
            track=1,
        )
        export_opus(
            in_wav,
            tmp_path / "out.opus",
            title="t",
            artist="a",
            album="b",
            track=1,
        )
    except RuntimeError as exc:
        # Missing ffmpeg; ensure message is informative
        assert "ffmpeg" in str(exc) or "pydub" in str(exc)

    write_chapter_cue([in_wav], tmp_path / "chapters.cue", ["One"])
    assert (tmp_path / "chapters.cue").exists()
