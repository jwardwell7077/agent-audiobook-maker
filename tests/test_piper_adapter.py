from pathlib import Path

from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import TTSTask


def test_piper_dryrun_writes_wav(tmp_path, monkeypatch):
    # Ensure dry-run for consistent CI
    monkeypatch.setenv("ABM_PIPER_DRYRUN", "1")
    ad = EngineRegistry.create("piper", voice="en_US-ryan-medium")
    ad.preload()
    out = ad.synth(
        TTSTask(
            text="Testing Piper dry run.",
            speaker="Narrator",
            engine="piper",
            voice="en_US-ryan-medium",
            profile_id=None,
            refs=[],
            out_path=tmp_path / "piper.wav",
            pause_ms=120,
            style="neutral",
        )
    )
    assert isinstance(out, Path)
    assert out.exists() and out.stat().st_size > 64
