from pathlib import Path

import pytest

from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import TTSAdapter, TTSTask


class NullAdapter(TTSAdapter):
    def preload(self) -> None:  # pragma: no cover - trivial
        pass

    def synth(self, task: TTSTask) -> Path:
        task.out_path.parent.mkdir(parents=True, exist_ok=True)
        task.out_path.write_bytes(b"RIFF\0\0\0\0WAVEfmt ")
        return task.out_path


def test_register_create_and_unregister(tmp_path):
    EngineRegistry.register("null", lambda **_: NullAdapter())
    try:
        assert "null" in EngineRegistry.list_engines()
        adapter = EngineRegistry.create("null")
        out_path = tmp_path / "out.wav"
        task = TTSTask(
            text="hi",
            speaker="Narrator",
            engine="null",
            voice=None,
            profile_id=None,
            refs=[],
            out_path=out_path,
            pause_ms=0,
            style="neutral",
        )
        adapter.preload()
        p = adapter.synth(task)
        assert p.exists()
    finally:
        EngineRegistry.unregister("null")
        assert "null" not in EngineRegistry.list_engines()
        EngineRegistry.unregister("null")  # no-op


def test_register_duplicate():
    EngineRegistry.register("dup", lambda **_: NullAdapter())
    with pytest.raises(ValueError):
        EngineRegistry.register("dup", lambda **_: NullAdapter())
    EngineRegistry.unregister("dup")


def test_create_unknown():
    with pytest.raises(KeyError):
        EngineRegistry.create("missing")


def test_tts_adapter_not_implemented(tmp_path):
    adapter = TTSAdapter()
    with pytest.raises(NotImplementedError):
        adapter.preload()
    task = TTSTask(
        text="hi",
        speaker="Narrator",
        engine="base",
        voice=None,
        profile_id=None,
        refs=[],
        out_path=tmp_path / "x.wav",
        pause_ms=0,
        style="neutral",
    )
    with pytest.raises(NotImplementedError):
        adapter.synth(task)
