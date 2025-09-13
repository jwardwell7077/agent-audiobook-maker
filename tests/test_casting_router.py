from __future__ import annotations

from dataclasses import asdict

from abm.profiles import ProfileConfig, SpeakerProfile, Style
from abm.voice import cast_speaker, merge_style


def _build_cfg() -> ProfileConfig:
    defaults = Style()
    speakers = {
        "narrator": SpeakerProfile(
            name="Narrator",
            engine="piper",
            voice="narrator_voice",
            style=Style(),
            aliases=[],
            fallback={"xtts": "narrator_xtts"},
        ),
        "alice": SpeakerProfile(
            name="Alice",
            engine="piper",
            voice="alice_voice",
            style=Style(pace=0.9),
            aliases=["Al"],
            fallback={"xtts": "alice_xtts"},
        ),
        "bob": SpeakerProfile(
            name="Bob",
            engine="piper",
            voice="bob_voice",
            style=Style(),
            aliases=[],
            fallback={},
        ),
    }
    return ProfileConfig(
        version=1,
        defaults_engine="piper",
        defaults_narrator_voice="narrator_voice",
        defaults_style=defaults,
        voices={
            "piper": ["narrator_voice", "alice_voice", "bob_voice"],
            "xtts": ["xtts_default"],
        },
        speakers=speakers,
    )


def test_cast_basic() -> None:
    cfg = _build_cfg()
    sel = cast_speaker(cfg, "Alice")
    assert sel.engine == "piper"
    assert sel.reason == "exact"
    assert sel.voice == "alice_voice"
    assert sel.engine_reason == "ok"

    sel_alias = cast_speaker(cfg, "Al")
    assert sel_alias.reason == "alias" and sel_alias.voice == "alice_voice"

    sel_sys = cast_speaker(cfg, "System")
    assert (
        sel_sys.reason == "narrator-fallback"
        and sel_sys.voice == "narrator_voice"
        and sel_sys.engine_reason == "ok"
    )

    sel_unknown = cast_speaker(cfg, "Ghost")
    assert (
        sel_unknown.reason == "narrator-fallback"
        and sel_unknown.voice == "narrator_voice"
    )

    cfg.voices["xtts"].append("alice_xtts")
    sel_xtts = cast_speaker(cfg, "Alice", prefer_engine="xtts")
    assert sel_xtts.engine == "xtts" and sel_xtts.voice == "alice_xtts"
    assert sel_xtts.engine_reason == "ok"

    sel_xtts_default = cast_speaker(cfg, "Bob", prefer_engine="xtts")
    assert (
        sel_xtts_default.engine == "xtts" and sel_xtts_default.voice == "xtts_default"
    )
    assert sel_xtts_default.style == merge_style(cfg.defaults_style, None)
    assert sel_xtts_default.engine_reason == "ok"


def test_fallback_and_determinism() -> None:
    cfg = _build_cfg()

    # engine missing -> engine-fallback via profile
    del cfg.voices["piper"]
    cfg.voices["xtts"].append("alice_xtts")
    sel_fb = cast_speaker(cfg, "Alice")
    assert sel_fb.engine == "xtts" and sel_fb.engine_reason == "engine-fallback"

    # voice missing -> voice-fallback within same engine
    cfg = _build_cfg()
    cfg.voices["piper"].remove("bob_voice")
    cfg.speakers["bob"].fallback["piper"] = "narrator_voice"
    sel_voice_fb = cast_speaker(cfg, "Bob")
    assert sel_voice_fb.engine == "piper"
    assert sel_voice_fb.voice == "narrator_voice"
    assert sel_voice_fb.engine_reason == "voice-fallback"

    # determinism
    cfg = _build_cfg()
    one = cast_speaker(cfg, "Alice")
    two = cast_speaker(cfg, "Alice")
    assert asdict(one) == asdict(two)
