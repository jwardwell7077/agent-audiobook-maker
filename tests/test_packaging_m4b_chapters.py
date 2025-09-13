import base64

import numpy as np
import pytest
import soundfile as sf

from abm.audio import packaging as pkg


def test_write_ffmetadata_chapters(tmp_path):
    chapters = [(0.0, 1.0, "Intro"), (1.0, 2.5, "Next")]
    out = tmp_path / "chapters.txt"
    pkg._write_ffmetadata_chapters(chapters, out)
    text = out.read_text()
    assert ";FFMETADATA1" in text
    assert text.count("[CHAPTER]") == 2
    assert "START=1000" in text
    assert "END=2500" in text


def test_make_chaptered_m4b_with_ffmpeg(tmp_path):
    if not pkg._have_ffmpeg():
        pytest.skip("ffmpeg not installed")
    pytest.importorskip("mutagen.mp4")

    sr = 48000
    y = np.zeros(int(sr * 0.3), dtype=np.float32)
    wavs = []
    for i in range(2):
        w = tmp_path / f"ch{i}.wav"
        sf.write(w, y, sr, subtype="PCM_16")
        wavs.append(w)

    cover = tmp_path / "cover.jpg"
    cover_bytes = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFwAAAwEAAAAAAAAAAAAAAAAAAAUGB//EABYBAQEBAAAAAAAAAAAAAAAAAAABAv/aAAwDAQACEAMQAAAByAAAAf/EABYQAQEBAAAAAAAAAAAAAAAAAAABEv/aAAgBAQABPwCz/8QAFhEBAQEAAAAAAAAAAAAAAAAAAQAx/9oACAECAQE/AWf/xAAWEQEBAQAAAAAAAAAAAAAAAAABEBH/2gAIAQMBAT8BY//Z"
    )
    cover.write_bytes(cover_bytes)

    out_m4b = tmp_path / "book.m4b"
    pkg.make_chaptered_m4b(
        wavs,
        out_m4b,
        ["One", "Two"],
        album="Album",
        artist="Artist",
        cover_jpeg=cover,
    )

    assert out_m4b.exists() and out_m4b.stat().st_size > 0

    from mutagen.mp4 import MP4

    mp4 = MP4(str(out_m4b))
    assert "covr" in mp4
