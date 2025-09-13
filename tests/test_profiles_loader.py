from __future__ import annotations

# isort: skip_file

import json
import textwrap
from pathlib import Path

from abm.profiles import (
    ProfileConfig,
    SpeakerProfile,
    Style,
    load_profiles,
    resolve_speaker,
    resolve_speaker_ex,
    validate_profiles,
)

# ruff: noqa: I001


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "cfg.yaml"
    p.write_text(textwrap.dedent(content))
    return p


def test_load_json(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "defaults": {"engine": "piper", "narrator_voice": "base"},
        "speakers": {"Narrator": {"engine": "piper", "voice": "base"}},
    }
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(data))
    cfg = load_profiles(p)
    assert cfg.version == 1
    assert resolve_speaker(cfg, "Narrator") is not None


def test_load_and_resolve_yaml(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
        version: 1
        defaults:
          engine: piper
          narrator_voice: base
        voices:
          piper: [base, bob_voice]
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
    prof, reason = resolve_speaker_ex(cfg, "Bobby")
    assert prof and prof.name == "Bob" and reason == "alias"
    prof, reason = resolve_speaker_ex(cfg, "ui")
    assert prof and prof.name == "Narrator" and reason == "narrator-fallback"
    assert resolve_speaker_ex(cfg, "Ghost")[1] == "unknown"
    assert resolve_speaker(cfg, "Bobby").name == "Bob"
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


def test_validate_unknown_engine_and_voice() -> None:
    cfg = ProfileConfig(
        version=1,
        defaults_engine="piper",
        defaults_narrator_voice="base",
        defaults_style=Style(),
        voices={"piper": ["base"]},
        speakers={
            "bad_engine": SpeakerProfile(
                name="BadE",
                engine="ghost",
                voice="v",
                style=Style(),
                aliases=[],
                fallback={},
            ),
            "bad_voice": SpeakerProfile(
                name="BadV",
                engine="piper",
                voice="nope",
                style=Style(),
                aliases=[],
                fallback={},
            ),
        },
    )
    issues = validate_profiles(cfg)
    assert any("unknown engine" in i for i in issues)
    assert any("unknown voice" in i for i in issues)


def test_validate_alias_collision() -> None:
    cfg = ProfileConfig(
        version=1,
        defaults_engine="piper",
        defaults_narrator_voice="base",
        defaults_style=Style(),
        voices={"piper": ["base"]},
        speakers={
            "a": SpeakerProfile(
                name="A",
                engine="piper",
                voice="base",
                style=Style(),
                aliases=["Sam"],
                fallback={},
            ),
            "b": SpeakerProfile(
                name="B",
                engine="piper",
                voice="base",
                style=Style(),
                aliases=["Sam"],
                fallback={},
            ),
        },
    )
    issues = validate_profiles(cfg)
    assert any("alias 'Sam'" in i for i in issues)


def test_validate_missing_narrator() -> None:
    cfg = ProfileConfig(
        version=1,
        defaults_engine="piper",
        defaults_narrator_voice="base",
        defaults_style=Style(),
        voices={"piper": ["base"]},
        speakers={},
    )
    issues = validate_profiles(cfg)
    assert any("narrator profile missing" in i for i in issues)


def test_validate_invalid_fallback() -> None:
    cfg = ProfileConfig(
        version=1,
        defaults_engine="piper",
        defaults_narrator_voice="base",
        defaults_style=Style(),
        voices={"piper": ["base"], "xtts": ["good"]},
        speakers={
            "a": SpeakerProfile(
                name="A",
                engine="piper",
                voice="base",
                style=Style(),
                aliases=[],
                fallback={"xtts": "bad"},
            ),
        },
    )
    issues = validate_profiles(cfg)
    assert any("fallback voice 'bad'" in i for i in issues)
