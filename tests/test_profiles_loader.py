from __future__ import annotations

import textwrap
from pathlib import Path

from abm.profiles import (
    ProfileConfig,
    SpeakerProfile,
    Style,
    load_profiles,
    resolve_speaker,
    validate_profiles,
)

# ruff: noqa: I001


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "cfg.yaml"
    p.write_text(textwrap.dedent(content))
    return p


def test_load_and_resolve(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        version: 1
        defaults:
          engine: piper
          narrator_voice: base
        speakers:
          Narrator:
            engine: piper
            voice: base
            aliases: [System]
          Bob:
            engine: piper
            voice: bob_voice
            aliases: [Bobby]
        """,
    )
    cfg = load_profiles(path)
    assert cfg.version == 1
    assert cfg.defaults_engine == "piper"
    assert "narrator" in cfg.speakers
    assert resolve_speaker(cfg, "Bobby").name == "Bob"
    assert resolve_speaker(cfg, "system").name == "Narrator"
    assert validate_profiles(cfg) == []


def test_validate_profiles_errors() -> None:
    bad = ProfileConfig(
        version=1,
        defaults_engine="piper",
        defaults_narrator_voice="",
        defaults_style=Style(),
        voices={},
        speakers={
            "bad": SpeakerProfile(
                name="Bad",
                engine="",
                voice="",
                style=Style(),
                aliases=[],
                fallback={},
            )
        },
    )
    issues = validate_profiles(bad)
    assert issues
