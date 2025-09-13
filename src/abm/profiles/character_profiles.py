"""Character profile loading and resolution utilities.

Profiles describe available voices, default rendering parameters, and
per-speaker overrides. They are stored as YAML or JSON files with the
following schema::

    version: 1
    defaults:
      engine: piper
      narrator_voice: en_US/ryan-high
      style:
        pace: 1.0
        energy: 0.9
        pitch: 0.0
        emotion: neutral
    voices:
      piper:
        - en_US/ryan-high
        - en_US/lessac-medium
      xtts:
        - qn_01
    speakers:
      Narrator:
        engine: piper
        voice: en_US/ryan-high
        aliases: [System, UI]
      Alice:
        engine: piper
        voice: en_US/lessac-medium
        fallback:
          xtts: qn_01
      Bob:
        engine: piper
        voice: en_US/lessac-medium

The loader accepts YAML via :func:`yaml.safe_load` when PyYAML is
available and falls back to JSON. Speaker names are normalized using
:func:`normalize_speaker_name`. :func:`resolve_speaker_ex` resolves
canonical names, aliases, or narrator-like terms such as ``System`` or
``UI`` and returns a reason code describing the match. Reason codes are:

``"exact"`` – exact name match
``"alias"`` – resolved via alias
``"narrator-fallback"`` – narrator/system/UI fallback
``"unknown"`` – no matching speaker
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from importlib import import_module
from types import ModuleType

yaml: Any | None = None
try:  # pragma: no cover - optional dependency
    yaml = import_module("yaml")
    HAVE_YAML = True
except Exception:  # pragma: no cover - YAML not installed
    HAVE_YAML = False

__all__ = [
    "Style",
    "SpeakerProfile",
    "ProfileConfig",
    "load_profiles",
    "validate_profiles",
    "normalize_speaker_name",
    "resolve_with_reason",
    "resolve_speaker_ex",
    "resolve_speaker",
    "available_voices",
]


@dataclass(slots=True)
class Style:
    """Prosody style parameters for a voice.

    Attributes:
        pace: Speech pace multiplier.
        energy: Vocal energy multiplier.
        pitch: Pitch offset in semitones.
        emotion: Optional emotion tag.
    """

    pace: float = 1.0
    energy: float = 0.9
    pitch: float = 0.0
    emotion: str = "neutral"


@dataclass(slots=True)
class SpeakerProfile:
    """Configuration for a single character voice.

    Attributes:
        name: Display name of the speaker.
        engine: Preferred TTS engine.
        voice: Voice identifier for the engine.
        style: Prosody style overrides.
        aliases: Alternative speaker names mapping to this profile.
        fallback: Mapping of engine name to fallback voice identifiers.
    """

    name: str
    engine: str
    voice: str
    style: Style
    aliases: list[str]
    fallback: dict[str, str]


@dataclass(slots=True)
class ProfileConfig:
    """Container for all profiles and defaults.

    Attributes:
        version: Schema version number.
        defaults_engine: Default TTS engine.
        defaults_narrator_voice: Default narrator voice identifier.
        defaults_style: Default style applied to all speakers.
        voices: Registry of available voices per engine.
        speakers: Mapping of normalized speaker names to profiles.
    """

    version: int
    defaults_engine: str
    defaults_narrator_voice: str
    defaults_style: Style
    voices: dict[str, list[str]]
    speakers: dict[str, SpeakerProfile]


# ---------------------------------------------------------------------------
# helpers


def normalize_speaker_name(name: str) -> str:
    """Normalize a speaker name to a comparison key.

    The function trims leading/trailing whitespace, collapses internal
    whitespace, and returns the casefolded result.

    Args:
        name: Raw speaker name.

    Returns:
        Normalized comparison key.
    """

    return " ".join(name.strip().split()).casefold()


def _style_from_dict(base: Style, data: dict[str, Any] | None) -> Style:
    base_d = asdict(base)
    if data:
        for k, v in data.items():
            if k in base_d:
                base_d[k] = v
    return Style(**base_d)


def load_profiles(path: str | Path) -> ProfileConfig:
    """Load a profile configuration file.

    The file may be YAML (preferred) or JSON. Names are normalized and stored
    by casefolded key.

    Args:
        path: Path to the YAML/JSON configuration.

    Returns:
        Parsed :class:`ProfileConfig` instance.

    Raises:
        RuntimeError: If the file cannot be read.
        ValueError: If the file content cannot be parsed.
    """

    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - rare
        raise RuntimeError(f"unable to read profiles file: {p}") from exc

    data: dict[str, Any]
    if HAVE_YAML and yaml is not None:
        try:  # pragma: no cover - exercised when yaml installed
            data = yaml.safe_load(text)
        except Exception:
            data = json.loads(text)
    else:
        data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("profiles file must contain a mapping")

    defaults = data.get("defaults", {}) or {}
    defaults_style = Style(**(defaults.get("style") or {}))
    speakers_cfg = data.get("speakers", {}) or {}

    speakers: dict[str, SpeakerProfile] = {}
    for raw_name, info in speakers_cfg.items():
        display = " ".join(str(raw_name).strip().split())
        key = normalize_speaker_name(display)
        engine = str(info.get("engine", defaults.get("engine", "")))
        voice = str(info.get("voice", defaults.get("narrator_voice", "")))
        style = _style_from_dict(defaults_style, info.get("style"))
        aliases = [" ".join(str(a).strip().split()) for a in info.get("aliases", [])]
        fallback = {str(k): str(v) for k, v in (info.get("fallback") or {}).items()}
        speakers[key] = SpeakerProfile(
            name=display,
            engine=engine,
            voice=voice,
            style=style,
            aliases=aliases,
            fallback=fallback,
        )

    cfg = ProfileConfig(
        version=int(data.get("version", 0)),
        defaults_engine=str(defaults.get("engine", "")),
        defaults_narrator_voice=str(defaults.get("narrator_voice", "")),
        defaults_style=defaults_style,
        voices={
            str(k): [str(v) for v in vs]
            for k, vs in (data.get("voices", {}) or {}).items()
        },
        speakers=speakers,
    )
    return cfg


def available_voices(cfg: ProfileConfig, engine: str) -> list[str]:
    """Return the declared voices for an engine."""

    return list(cfg.voices.get(engine, []))


# ---------------------------------------------------------------------------
# resolution & validation


def _resolve_with_reason(
    cfg: ProfileConfig, speaker: str
) -> tuple[SpeakerProfile | None, str]:
    """Internal helper returning a profile and match reason."""

    normalized = normalize_speaker_name(speaker)
    if normalized in cfg.speakers:
        return cfg.speakers[normalized], "exact"
    for sp in cfg.speakers.values():
        if any(normalize_speaker_name(a) == normalized for a in sp.aliases):
            return sp, "alias"
    narrator_key = normalize_speaker_name("Narrator")
    if normalized in {"narrator", "system", "ui"} and narrator_key in cfg.speakers:
        return cfg.speakers[narrator_key], "narrator-fallback"
    return None, "unknown"


def resolve_speaker_ex(
    cfg: ProfileConfig, speaker: str
) -> tuple[SpeakerProfile | None, str]:
    """Return the resolved profile and reason for ``speaker``.

    Args:
        cfg: Loaded profile configuration.
        speaker: Name to resolve.

    Returns:
        Tuple ``(profile, reason)`` where *profile* is the matching
        :class:`SpeakerProfile` or ``None`` and *reason* is one of
        ``{"exact", "alias", "narrator-fallback", "unknown"}``.
    """

    return _resolve_with_reason(cfg, speaker)


def resolve_with_reason(
    cfg: ProfileConfig, speaker: str
) -> tuple[SpeakerProfile | None, str]:
    """Backward compatible wrapper around :func:`resolve_speaker_ex`."""

    return resolve_speaker_ex(cfg, speaker)


def resolve_speaker(cfg: ProfileConfig, speaker: str) -> SpeakerProfile | None:
    """Resolve ``speaker`` to a profile using canonical names or aliases."""

    return resolve_speaker_ex(cfg, speaker)[0]


def validate_profiles(cfg: ProfileConfig) -> list[str]:
    """Validate a profile configuration.

    Args:
        cfg: Loaded profile configuration.

    Returns:
        A list of human readable issues. The list is empty when the
        configuration is valid.
    """

    issues: list[str] = []
    if cfg.version != 1:
        issues.append("version must be 1")
    if not cfg.defaults_engine:
        issues.append("defaults.engine missing")
    if not cfg.defaults_narrator_voice:
        issues.append("defaults.narrator_voice missing")

    if resolve_speaker(cfg, "Narrator") is None:
        issues.append("narrator profile missing")

    canonical = set(cfg.speakers.keys())
    alias_map: dict[str, str] = {}
    for sp in cfg.speakers.values():
        if not sp.engine:
            issues.append(f"speaker '{sp.name}' missing engine")
        if not sp.voice:
            issues.append(f"speaker '{sp.name}' missing voice")
        if sp.engine not in cfg.voices:
            issues.append(
                f"speaker '{sp.name}' references unknown engine '{sp.engine}'"
            )
        elif sp.voice not in cfg.voices.get(sp.engine, []):
            issues.append(
                f"speaker '{sp.name}' references unknown voice '{sp.voice}' for engine '{sp.engine}'"
            )
        for alias in sp.aliases:
            norm = normalize_speaker_name(alias)
            if norm in canonical:
                issues.append(f"alias '{alias}' conflicts with existing speaker")
            if norm in alias_map:
                issues.append(
                    f"alias '{alias}' claimed by '{alias_map[norm]}' and '{sp.name}'"
                )
            alias_map[norm] = sp.name
        for eng, voice in sp.fallback.items():
            if eng not in cfg.voices:
                issues.append(f"speaker '{sp.name}' fallback engine '{eng}' unknown")
            elif voice not in cfg.voices[eng]:
                issues.append(
                    f"speaker '{sp.name}' fallback voice '{voice}' unknown for engine '{eng}'"
                )
    return issues
    
