"""Routing of speakers to TTS engine selections."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from abm.profiles import ProfileConfig, Style, resolve_speaker_ex

__all__ = ["CastDecision", "pick_voice", "merge_style"]


@dataclass(slots=True)
class CastDecision:
    """Final TTS selection for a speaker.

    Attributes:
        speaker: Original speaker query.
        engine: Selected TTS engine name.
        voice: Voice identifier within the engine.
        style: Prosody style applied to synthesis.
        method: How the selection was made. One of
            ``{"profile", "alias", "narrator-fallback", "fallback-voice", "default"}``.
        reason: Resolution reason from :func:`resolve_speaker_ex` or a note.
    """

    speaker: str
    engine: str
    voice: str
    style: Style
    method: str
    reason: str


def merge_style(base: Style, override: Style | dict[str, Any] | None) -> Style:
    """Merge style overrides onto ``base``.

    Args:
        base: Base style dataclass.
        override: Optional overriding style or dictionary.

    Returns:
        New :class:`Style` with values from ``override`` replacing ``base``.
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


def _voice_ok(cfg: ProfileConfig, engine: str, voice: str) -> bool:
    """Return ``True`` if ``voice`` exists for ``engine`` in ``cfg``."""

    return voice in cfg.voices.get(engine, [])


def pick_voice(
    cfg: ProfileConfig,
    speaker_name: str,
    *,
    preferred_engine: str | None = None,
) -> CastDecision:
    """Choose engine, voice and style for ``speaker_name``.

    Args:
        cfg: Loaded profile configuration.
        speaker_name: Speaker name as annotated.
        preferred_engine: Optional engine to force when available.

    Returns:
        A :class:`CastDecision` describing the selection.
    """

    profile, reason = resolve_speaker_ex(cfg, speaker_name)
    if profile:
        engine = preferred_engine or profile.engine
        voice = profile.voice
        style = merge_style(cfg.defaults_style, profile.style)
        if reason == "exact":
            method = "profile"
        elif reason == "alias":
            method = "alias"
        else:
            method = "narrator-fallback"
        if not _voice_ok(cfg, engine, voice):
            fb = profile.fallback.get(engine)
            if fb and _voice_ok(cfg, engine, fb):
                voice = fb
                method = "fallback-voice"
            else:
                engine = cfg.defaults_engine
                voice = cfg.defaults_narrator_voice
                style = cfg.defaults_style
                method = "default"
    else:
        engine = cfg.defaults_engine
        voice = cfg.defaults_narrator_voice
        style = cfg.defaults_style
        method = "narrator-fallback" if reason == "narrator-fallback" else "default"
        if method == "default":
            reason = "unknown"

    return CastDecision(
        speaker=speaker_name,
        engine=engine,
        voice=voice,
        style=style,
        method=method,
        reason=reason,
    )
