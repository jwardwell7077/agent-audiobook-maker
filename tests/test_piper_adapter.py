import subprocess
from pathlib import Path

import pytest

from abm.audio import register_builtins
from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import SynthesisError, TTSTask


def test_piper_dryrun_writes_wav(tmp_path, monkeypatch):
    register_builtins()
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


def test_piper_timeout(tmp_path, monkeypatch):
    register_builtins()
    monkeypatch.delenv("ABM_PIPER_DRYRUN", raising=False)
    ad = EngineRegistry.create("piper", voice="en_US-ryan-medium")
    ad._dryrun = False
    ad._available = True

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=60)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SynthesisError):
        ad.synth(
            TTSTask(
                text="Hello",
                speaker="N",
                engine="piper",
                voice="en_US-ryan-medium",
                profile_id=None,
                refs=[],
                out_path=tmp_path / "piper.wav",
                pause_ms=120,
                style="neutral",
            )
        )
