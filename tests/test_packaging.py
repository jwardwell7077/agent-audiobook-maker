import numpy as np
import pytest
import soundfile as sf

from abm.audio import package_book
from abm.audio.packaging import export_mp3, export_opus, format_ts


def test_format_ts_edges():
    assert format_ts(0.0) == "00:00:00.000"
    assert format_ts(0.123) == "00:00:00.123"
    assert format_ts(3661.5) == "01:01:01.500"


def test_exporters_missing_tools(tmp_path, monkeypatch):
    monkeypatch.setattr("abm.audio.packaging.importlib.util.find_spec", lambda _: None)
    monkeypatch.setattr("abm.audio.packaging.shutil.which", lambda _: None)
    wav = tmp_path / "in.wav"
    sf.write(wav, np.zeros(10, dtype=np.float32), 16000)
    with pytest.raises(RuntimeError):
        export_mp3(wav, tmp_path / "o.mp3", title="t", artist="a", album="b", track=1)
    with pytest.raises(RuntimeError):
        export_opus(wav, tmp_path / "o.opus", title="t", artist="a", album="b", track=1)


def test_package_book_skips_formats(tmp_path, monkeypatch):
    monkeypatch.setattr("abm.audio.packaging.importlib.util.find_spec", lambda _: None)
    monkeypatch.setattr("abm.audio.packaging.shutil.which", lambda _: None)
    renders = tmp_path / "renders"
    renders.mkdir()
    wav = renders / "ch_0001.wav"
    sf.write(wav, np.zeros(10, dtype=np.float32), 16000)
    cover = tmp_path / "c.jpg"
    cover.write_bytes(b"\x00")
    meta = tmp_path / "book.yaml"
    meta.write_text(
        f"""
        title: Test
        author: A
        series: S
        language: en
        year: 2020
        cover: {cover}
        publisher: P
        """
    )
    out = tmp_path / "out"
    produced = package_book.package_book(renders, meta, out, ["mp3", "opus"])
    assert out / "ch_0001.chapters.txt" in produced
    assert not any(p.suffix in {".mp3", ".opus"} for p in produced)
