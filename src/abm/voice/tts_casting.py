"""Routing of speakers to TTS engine selections."""

# ruff: noqa: I001

from dataclasses import asdict, dataclass
from typing import Any

from abm.profiles.character_profiles import ProfileConfig, Style, _resolve_with_reason

__all__ = ["EngineSelection", "cast_speaker", "merge_style"]


@dataclass(slots=True)
class EngineSelection:
    """Result of casting a speaker to a voice engine.

    Attributes:
        engine: Selected TTS engine name.
        voice: Voice identifier for the engine.
        style: Merged style dictionary.
        refs: Optional reference clips for cloning.
        reason: Resolution reason (exact, alias, narrator-fallback, unknown).
    """

    engine: str
    voice: str
    style: dict[str, Any]
    refs: list[str]
    reason: str


def merge_style(base: Style, override: Style | dict[str, Any] | None) -> dict[str, Any]:
    """Merge style overrides onto a base style.

    Args:
        base: Base style dataclass.
        override: Optional overriding style or dictionary.

    Returns:
        A merged dictionary where override values replace base values.
    """

    merged = asdict(base)
    if override is None:
        return merged
    if isinstance(override, Style):
        override = asdict(override)
    for k, v in override.items():
        if k in merged and v is not None:
            merged[k] = v
    return merged


def cast_speaker(
    cfg: ProfileConfig,
    speaker: str,
    *,
    prefer_engine: str | None = None,
    default_refs: list[str] | None = None,
) -> EngineSelection:
    """Resolve a speaker to an engine and voice.

    Args:
        cfg: Loaded profile configuration.
        speaker: Speaker name as annotated.
        prefer_engine: Optional engine preference to override profile engine.
        default_refs: Optional reference clips for cloning engines.

    Returns:
        An :class:`EngineSelection` describing the choice.
    """

    profile, reason = _resolve_with_reason(cfg, speaker)
    refs = default_refs or []

    if profile:
        style = merge_style(cfg.defaults_style, profile.style)
        engine = profile.engine
        voice = profile.voice
        if prefer_engine and prefer_engine != profile.engine:
            if prefer_engine in profile.fallback:
                engine = prefer_engine
                voice = profile.fallback[prefer_engine]
            elif cfg.voices.get(prefer_engine):
                engine = prefer_engine
                voice = cfg.voices[prefer_engine][0]
                style = merge_style(cfg.defaults_style, None)
        refs = refs if engine != "piper" else []
    else:
        engine = cfg.defaults_engine
        voice = cfg.defaults_narrator_voice
        style = merge_style(cfg.defaults_style, None)
        refs = refs if engine != "piper" else []
        if reason != "narrator-fallback":
            reason = "unknown"

    return EngineSelection(
        engine=engine, voice=voice, style=style, refs=refs, reason=reason
    )
