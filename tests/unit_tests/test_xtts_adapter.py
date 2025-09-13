from pathlib import Path

import pytest

from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import SynthesisError, TTSTask
from abm.audio.xtts_adapter import XTTSAdapter, _write_sine_wav


def test_write_sine(tmp_path: Path) -> None:
    path = tmp_path / "sine.wav"
    _write_sine_wav(path, duration_ms=100)
    assert path.exists() and path.stat().st_size > 40


def test_engine_registry_create() -> None:
    adapter = EngineRegistry.create("xtts", device="cpu")
    assert isinstance(adapter, XTTSAdapter)


def test_engine_registry_unknown() -> None:
    with pytest.raises(KeyError):
        EngineRegistry.create("missing")


def test_xtts_dryrun(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ABM_XTTS_DRYRUN", "1")
    adapter = XTTSAdapter(device="cpu")
    adapter.preload()  # no-op in dry run
    task = TTSTask("hello", "voice", "xtts", None, None, out_path=tmp_path / "out.wav")
    adapter.synth(task)
    assert task.out_path.exists() and task.out_path.stat().st_size > 40


def test_xtts_empty_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ABM_XTTS_DRYRUN", "1")
    adapter = XTTSAdapter(device="cpu")
    task = TTSTask("", "voice", "xtts", None, None, out_path=tmp_path / "out.wav")
    adapter.synth(task)
    assert task.out_path.exists()


def test_xtts_not_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ABM_XTTS_DRYRUN", raising=False)
    adapter = XTTSAdapter(device="cpu")
    task = TTSTask("hi", "voice", "xtts", None, None, out_path=tmp_path / "out.wav")
    with pytest.raises(SynthesisError):
        adapter.synth(task)


def test_split_sentences() -> None:
    adapter = XTTSAdapter()
    text = "Hi there. How are you? Great!"
    assert adapter._split_sentences(text) == ["Hi there.", "How are you?", "Great!"]
