from __future__ import annotations

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
    assert (
        sel.engine == "piper" and sel.reason == "exact" and sel.voice == "alice_voice"
    )

    sel_alias = cast_speaker(cfg, "Al")
    assert sel_alias.reason == "alias" and sel_alias.voice == "alice_voice"

    sel_sys = cast_speaker(cfg, "System")
    assert sel_sys.reason == "narrator-fallback" and sel_sys.voice == "narrator_voice"

    sel_unknown = cast_speaker(cfg, "Ghost")
    assert sel_unknown.reason == "unknown" and sel_unknown.voice == "narrator_voice"

    sel_xtts = cast_speaker(cfg, "Alice", prefer_engine="xtts")
    assert sel_xtts.engine == "xtts" and sel_xtts.voice == "alice_xtts"

    sel_xtts_default = cast_speaker(cfg, "Bob", prefer_engine="xtts")
    assert (
        sel_xtts_default.engine == "xtts" and sel_xtts_default.voice == "xtts_default"
    )
    assert sel_xtts_default.style == merge_style(cfg.defaults_style, None)
