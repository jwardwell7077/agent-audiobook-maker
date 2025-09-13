import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from abm.audio.album_norm import (
    apply_album_gain,
    collect_chapter_stats,
    compute_album_offset,
    write_album_manifest,
)
from abm.audio.engine_registry import EngineRegistry
from abm.audio.packaging import (
    export_mp3,
    export_opus,
    format_ts,
    make_chaptered_m4b,
    write_chapter_cue,
)
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
        "--scripts-dir",
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
    assert manifest["base_dir"] == str(out_dir)

    EngineRegistry.unregister("dummy")


def test_render_book_cli_args(capsys):
    with pytest.raises(SystemExit):
        render_book_main(["--help"])
    out = capsys.readouterr().out
    assert "--scripts-dir" in out
    assert "--log-level" in out


def test_render_book_no_scripts(tmp_path, caplog):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    out_dir = tmp_path / "out"
    argv = [
        "--scripts-dir",
        str(scripts_dir),
        "--out-dir",
        str(out_dir),
        "--engine-workers",
        "{}",
    ]
    with caplog.at_level("WARNING"):
        ret = render_book_main(argv)
    assert ret == 0
    manifest = json.loads((out_dir / "manifests" / "book_manifest.json").read_text())
    assert manifest["chapters"] == []
    assert manifest["base_dir"] == str(out_dir)


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
        "base_dir": str(tmp_path),
        "chapters": [
            {"index": 0, "qc_path": f"qc/{qc0.name}", "wav_path": wav0.name},
            {"index": 1, "qc_path": f"qc/{qc1.name}", "wav_path": wav1.name},
        ],
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


def test_collect_stats_without_base_dir(tmp_path):
    wav = tmp_path / "ch_000.wav"
    sf.write(wav, np.zeros(10), 16000)
    qc = tmp_path / "ch_000.qc.json"
    qc.write_text(json.dumps({"duration_s": 0.1, "integrated_lufs": -20}))
    manifest_path = tmp_path / "book_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {"chapters": [{"index": 0, "qc_path": qc.name, "wav_path": wav.name}]}
        )
    )
    stats = collect_chapter_stats(manifest_path)
    assert stats[0]["duration_s"] == 0.1


def test_compute_album_offset_trim():
    stats = [{"integrated_lufs": v} for v in [-10, -10, -10, -100, 0]]
    offset = compute_album_offset(stats, target_lufs=-20.0, trim_percent=0.2)
    assert offset == pytest.approx(-10.0)
    small = [{"integrated_lufs": -20.0}, {"integrated_lufs": -10.0}]
    offset2 = compute_album_offset(small, target_lufs=-18.0, trim_percent=0.1)
    assert offset2 == pytest.approx(-3.0)


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0.0, "00:00:00.000"),
        (59.999, "00:00:59.999"),
        (60.0, "00:01:00.000"),
        (3600.5, "01:00:00.500"),
    ],
)
def test_format_ts(seconds, expected):
    assert format_ts(seconds) == expected


def test_write_chapter_cue(tmp_path):
    sr = 48000
    wav0 = tmp_path / "0.wav"
    wav1 = tmp_path / "1.wav"
    sf.write(wav0, np.zeros(int(sr * 0.5)), sr)
    sf.write(wav1, np.zeros(int(sr * 0.25)), sr)
    out_cue = tmp_path / "c.cue"
    write_chapter_cue([wav0, wav1], out_cue, ["A", "B"])
    lines = out_cue.read_text().strip().splitlines()
    assert lines[0].startswith("00:00:00.000")
    assert lines[1].startswith("00:00:00.500")


def test_packaging_requires_ffmpeg(tmp_path, monkeypatch):
    def boom():  # pragma: no cover - simulated missing dep
        raise RuntimeError("pydub/ffmpeg required for packaging")

    monkeypatch.setattr(
        "abm.audio.packaging.importlib.util.find_spec", lambda name: None
    )
    monkeypatch.setattr("abm.audio.packaging.shutil.which", lambda name: None)
    wav = tmp_path / "in.wav"
    sf.write(wav, np.zeros(10), 16000)
    with pytest.raises(RuntimeError, match="pydub/ffmpeg"):
        export_mp3(wav, tmp_path / "o.mp3", title="t", artist="a", album="b", track=1)
    with pytest.raises(RuntimeError, match="pydub/ffmpeg"):
        export_opus(wav, tmp_path / "o.opus", title="t", artist="a", album="b", track=1)
    monkeypatch.setattr("abm.audio.packaging._require_pydub", boom)
    with pytest.raises(RuntimeError, match="pydub/ffmpeg"):
        make_chaptered_m4b([wav], tmp_path / "o.m4b", ["One"], album="a", artist="b")


def test_make_chaptered_m4b_errors(tmp_path):
    wav = tmp_path / "c.wav"
    sf.write(wav, np.zeros(10), 16000)
    with pytest.raises(ValueError):
        make_chaptered_m4b([wav], tmp_path / "o.m4b", [], album="a", artist="b")
    with pytest.raises(FileNotFoundError):
        make_chaptered_m4b(
            [wav],
            tmp_path / "o.m4b",
            ["One"],
            album="a",
            artist="b",
            cover_jpeg=tmp_path / "missing.jpg",
        )


def test_packaging_success_paths(tmp_path, monkeypatch):
    exports: list[tuple[str, dict | None]] = []

    class DummySeg:
        def __init__(self, duration: float = 0.1) -> None:
            self.duration_seconds = duration

        @classmethod
        def from_wav(cls, path: str) -> "DummySeg":  # pragma: no cover - simple
            return cls()

        @staticmethod
        def silent(ms: int) -> "DummySeg":  # pragma: no cover - simple
            return DummySeg(ms / 1000)

        def export(self, out_path, format, tags=None, cover=None) -> None:  # noqa: D401
            Path(out_path).touch()
            exports.append((format, tags))

        def __add__(self, other: "DummySeg") -> "DummySeg":  # pragma: no cover
            return DummySeg(self.duration_seconds + other.duration_seconds)

    monkeypatch.setattr(
        "abm.audio.packaging.importlib.util.find_spec", lambda name: object()
    )
    monkeypatch.setattr("abm.audio.packaging.shutil.which", lambda name: "ffmpeg")
    monkeypatch.setattr("abm.audio.packaging._require_pydub", lambda: DummySeg)
    monkeypatch.setattr("abm.audio.packaging._have_ffmpeg", lambda: False)

    wav = tmp_path / "in.wav"
    sf.write(wav, np.zeros(10), 16000)
    export_mp3(wav, tmp_path / "o.mp3", title="t", artist="a", album="b", track=1)
    export_opus(wav, tmp_path / "o.opus", title="t", artist="a", album="b", track=1)
    make_chaptered_m4b(
        [wav, wav], tmp_path / "out.m4b", ["A", "B"], album="a", artist="b"
    )
    assert (tmp_path / "out.chapters.txt").exists()
    assert exports[0][1]["tracknumber"] == "1"
    assert exports[1][1]["tracknumber"] == "1"
