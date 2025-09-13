from __future__ import annotations

from dataclasses import asdict

from abm.profiles import ProfileConfig, SpeakerProfile, Style
from abm.voice import pick_voice


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


def test_pick_voice_paths() -> None:
    cfg = _build_cfg()
    sel = pick_voice(cfg, "Alice")
    assert sel.engine == "piper" and sel.voice == "alice_voice"
    assert sel.method == "profile" and sel.reason == "exact"

    sel_alias = pick_voice(cfg, "Al")
    assert sel_alias.method == "alias" and sel_alias.reason == "alias"

    sel_sys = pick_voice(cfg, "System")
    assert sel_sys.method == "narrator-fallback" and sel_sys.voice == "narrator_voice"

    sel_unknown = pick_voice(cfg, "Ghost")
    assert sel_unknown.method == "default" and sel_unknown.reason == "unknown"

    cfg.voices["xtts"].append("alice_xtts")
    sel_pref = pick_voice(cfg, "Alice", preferred_engine="xtts")
    assert sel_pref.engine == "xtts" and sel_pref.voice == "alice_xtts"
    assert sel_pref.method == "fallback-voice"

    cfg = _build_cfg()
    cfg.voices["piper"].remove("bob_voice")
    cfg.speakers["bob"].fallback["piper"] = "narrator_voice"
    sel_fb = pick_voice(cfg, "Bob")
    assert sel_fb.voice == "narrator_voice" and sel_fb.method == "fallback-voice"

    cfg = _build_cfg()
    one = pick_voice(cfg, "Alice")
    two = pick_voice(cfg, "Alice")
    assert asdict(one) == asdict(two)
