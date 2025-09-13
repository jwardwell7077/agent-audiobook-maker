"""Routing of speakers to TTS engine selections.

Example
-------
A minimal casting flow::

    >>> from abm.profiles import ProfileConfig, SpeakerProfile, Style
    >>> cfg = ProfileConfig(
    ...     version=1,
    ...     defaults_engine="piper",
    ...     defaults_narrator_voice="narrator",
    ...     defaults_style=Style(),
    ...     voices={"piper": ["narrator", "alice"]},
    ...     speakers={
    ...         "narrator": SpeakerProfile(
    ...             name="Narrator",
    ...             engine="piper",
    ...             voice="narrator",
    ...             style=Style(),
    ...             aliases=["System"],
    ...             fallback={},
    ...         ),
    ...     },
    ... )
    >>> from abm.voice.tts_casting import cast_speaker
    >>> cast_speaker(cfg, "System").engine
    'piper'

Resolution reasons returned by :func:`cast_speaker` mirror those from
``resolve_with_reason``: ``{"exact", "alias", "narrator-fallback",
"unknown"}``. ``engine_reason`` records whether the selected engine/voice
comes directly from the profile (``"ok"``), from a profile fallback
(``"engine-fallback"`` or ``"voice-fallback"``), or from the global
defaults (``"defaults-fallback"``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from abm.profiles import ProfileConfig, Style, resolve_with_reason

__all__ = ["CastingDecision", "cast_speaker", "merge_style"]


@dataclass(slots=True)
class CastingDecision:
    """Result of casting a speaker to a voice engine.

    Attributes:
        speaker: Original speaker query.
        engine: Selected TTS engine name.
        voice: Voice identifier for the engine.
        style: Final style applied to synthesis.
        refs: Optional reference clips for cloning engines.
        reason: Resolution reason ``{"exact", "alias", "narrator-fallback", "unknown"}``.
        engine_reason: Explanation for engine/voice selection. One of
            ``"ok"``, ``"engine-fallback"``, ``"voice-fallback"`` or
            ``"defaults-fallback"``.
    """

    speaker: str
    engine: str
    voice: str
    style: Style
    refs: list[str]
    reason: str
    engine_reason: str | None


def merge_style(base: Style, override: Style | dict[str, Any] | None) -> Style:
    """Merge style overrides onto a base style.

    Args:
        base: Base style dataclass.
        override: Optional overriding style or dictionary.

    Returns:
        A new :class:`Style` where override values replace base values.
    """

    merged = asdict(base)
    if override is None:
        return Style(**merged)
    if isinstance(override, Style):
        override = asdict(override)
    for k, v in override.items():
        if k in merged and v is not None:
            merged[k] = v
    return Style(**merged)


def cast_speaker(
    cfg: ProfileConfig,
    speaker: str,
    *,
    prefer_engine: str | None = None,
    default_refs: list[str] | None = None,
) -> CastingDecision:
    """Return engine, voice and style for ``speaker``.

    Args:
        cfg: Loaded profile configuration.
        speaker: Speaker name as annotated.
        prefer_engine: Optional engine preference to override profile engine.
        default_refs: Optional reference clips for cloning engines.

    Returns:
        A :class:`CastingDecision` describing the choice.
    """

    profile, reason = resolve_with_reason(cfg, speaker)
    refs = default_refs or []

    if profile is None:
        profile, _ = resolve_with_reason(cfg, "Narrator")
        engine = cfg.defaults_engine
        voice = cfg.defaults_narrator_voice
        style = merge_style(cfg.defaults_style, profile.style if profile else None)
        reason = "narrator-fallback"
    else:
        engine = profile.engine
        voice = profile.voice
        style = merge_style(cfg.defaults_style, profile.style)

    if profile and prefer_engine and prefer_engine != engine:
        if prefer_engine in profile.fallback:
            engine = prefer_engine
            voice = profile.fallback[prefer_engine]
        elif cfg.voices.get(prefer_engine):
            engine = prefer_engine
            voice = cfg.voices[prefer_engine][0]
            style = merge_style(cfg.defaults_style, None)

    refs = refs if engine != "piper" else []

    engine_reason: str | None = "ok"
    if engine not in cfg.voices or voice not in cfg.voices.get(engine, []):
        engine_reason = None
        if profile:
            for eng, v in profile.fallback.items():
                if eng in cfg.voices and v in cfg.voices[eng]:
                    engine = eng
                    voice = v
                    engine_reason = (
                        "engine-fallback" if eng != profile.engine else "voice-fallback"
                    )
                    break
        if engine_reason is None:
            engine = cfg.defaults_engine
            voice = cfg.defaults_narrator_voice
            style = merge_style(cfg.defaults_style, None)
            engine_reason = "defaults-fallback"

    refs = refs if engine != "piper" else []

    return CastingDecision(
        speaker=speaker,
        engine=engine,
        voice=voice,
        style=style,
        refs=refs,
        reason=reason,
        engine_reason=engine_reason,
    )
