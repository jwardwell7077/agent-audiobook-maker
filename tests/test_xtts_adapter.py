from pathlib import Path

from abm.audio import register_builtins
from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import TTSTask


def test_xtts_dryrun_writes_wav(tmp_path, monkeypatch):
    register_builtins()
    monkeypatch.setenv("ABM_XTTS_DRYRUN", "1")
    ad = EngineRegistry.create("xtts")
    ad.preload()
    out = ad.synth(
        TTSTask(
            text="A calm line for XTTS.",
            speaker="Quinn",
            engine="xtts",
            voice=None,
            profile_id="quinn_v1",
            refs=[],
            out_path=tmp_path / "xtts.wav",
            pause_ms=120,
            style="calm",
        )
    )
    assert isinstance(out, Path)
    assert out.exists() and out.stat().st_size > 100
