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

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore

    HAVE_YAML = True
except Exception:  # pragma: no cover - YAML not installed
    yaml = None
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
    # Lightweight DB types used by alias resolver and casting
    "Profile",
    "CharacterProfilesDB",
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
    if HAVE_YAML:
        assert yaml is not None  # for type checkers
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
        voices={str(k): [str(v) for v in vs] for k, vs in (data.get("voices", {}) or {}).items()},
        speakers=speakers,
    )
    return cfg


def available_voices(cfg: ProfileConfig, engine: str) -> list[str]:
    """Return the declared voices for an engine."""

    return list(cfg.voices.get(engine, []))


# ---------------------------------------------------------------------------
# Lightweight DB for aliasing and casting (JSON/YAML interchangeable)


@dataclass(slots=True)
class Profile:
    """Minimal voice profile used by casting and alias resolver.

    Attributes:
        id: Stable identifier for the profile.
        label: Human-readable label (often the speaker name).
        engine: Preferred TTS engine.
        voice: Voice identifier for the engine.
        refs: Optional reference file paths or notes.
        style: Free-form style tag or preset name.
        tags: Additional tags used for fuzzy casting (e.g. ["narrator"]).
    """

    id: str
    label: str
    engine: str
    voice: str
    refs: list[str]
    style: str
    tags: list[str] | None = None


class CharacterProfilesDB:
    """Unified view over profiles with helpers for casting/aliasing.

    The database can be loaded from two on-disk schemas:
    - JSON (tests and tools):
        {
          "profiles": [{...}],
          "map": {"Speaker": "profile_id"},
          "fallbacks": {"engine": "profile_id"}
        }
    - YAML (human-edited casting file):
        version: 1
        defaults: { engine: ..., narrator_voice: ... }
        voices: { engine: [voices...] }
        speakers: { Name: { engine: ..., voice: ..., aliases: [...] } }

    In-memory representation keeps:
        profiles: dict[id -> Profile]
        speaker_map: dict[speaker_name -> Profile]
        fallbacks: dict[engine -> Profile]
    """

    def __init__(
        self,
        *,
        profiles: dict[str, Profile] | None = None,
        speaker_map: dict[str, str | Profile] | None = None,
        fallbacks: dict[str, str | Profile] | None = None,
    ) -> None:
        self.profiles: dict[str, Profile] = profiles or {}
        # Internally store speaker_map/fallbacks as Profile objects
        self.speaker_map: dict[str, Profile] = {}
        if speaker_map:
            for name, ref in speaker_map.items():
                prof = self._resolve_profile_ref(ref)
                if prof:
                    self.speaker_map[name] = prof
        self.fallbacks: dict[str, Profile] = {}
        if fallbacks:
            for eng, ref in fallbacks.items():
                prof = self._resolve_profile_ref(ref)
                if prof:
                    self.fallbacks[str(eng)] = prof

    # ------------------------------- I/O ----------------------------------

    @staticmethod
    def load(path: str | Path) -> CharacterProfilesDB:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        # Prefer JSON if it looks like JSON, otherwise try YAML
        data: Any
        try:
            data = json.loads(text)
            return CharacterProfilesDB._from_json_dict(data)
        except Exception:
            if not HAVE_YAML:
                raise
            assert yaml is not None
            data = yaml.safe_load(text)
            return CharacterProfilesDB._from_yaml_dict(data)

    def save(self, path: str | Path) -> None:
        """Persist as JSON for tool friendliness.

        Note: We intentionally write JSON regardless of input format to keep
        the operation deterministic and side-effect free (YAML is typically a
        hand-edited source of truth). Tools can always re-export to YAML later.
        """

        out = self._to_json_dict()
        Path(path).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")

    # ------------------------------- Queries ------------------------------

    def by_speaker(self, name: str) -> Profile | None:
        # exact
        if name in self.speaker_map:
            return self.speaker_map[name]
        # case-insensitive / normalised
        key = normalize_speaker_name(name)
        for k, v in self.speaker_map.items():
            if normalize_speaker_name(k) == key:
                return v
        return None

    def fallback(self, engine: str) -> Profile:
        if engine in self.fallbacks:
            return self.fallbacks[engine]
        # Any narrator-like profile
        for prof in self.profiles.values():
            tags = prof.tags or []
            if any(t.lower() == "narrator" for t in tags) or prof.label.lower() == "narrator":
                return prof
        # else first available
        return next(iter(self.profiles.values()))

    # ------------------------------- Helpers ------------------------------

    def _resolve_profile_ref(self, ref: str | Profile | None) -> Profile | None:
        if ref is None:
            return None
        if isinstance(ref, Profile):
            return ref
        # by id
        prof = self.profiles.get(ref)
        if prof:
            return prof
        # by label (common in YAML speaker maps)
        for p in self.profiles.values():
            if p.label == ref:
                return p
        return None

    def _to_json_dict(self) -> dict[str, Any]:
        return {
            "profiles": [
                {
                    "id": p.id,
                    "label": p.label,
                    "engine": p.engine,
                    "voice": p.voice,
                    "refs": p.refs,
                    "style": p.style,
                    **({"tags": p.tags} if p.tags is not None else {}),
                }
                for p in self.profiles.values()
            ],
            "map": {name: prof.id for name, prof in self.speaker_map.items()},
            "fallbacks": {eng: prof.id for eng, prof in self.fallbacks.items()},
        }

    @staticmethod
    def _from_json_dict(data: Any) -> CharacterProfilesDB:
        if not isinstance(data, dict):
            raise ValueError("profiles DB must be a mapping")
        profs: dict[str, Profile] = {}
        for item in data.get("profiles", []) or []:
            prof = Profile(
                id=str(item["id"]),
                label=str(item.get("label", str(item["id"]))),
                engine=str(item.get("engine", "")),
                voice=str(item.get("voice", "")),
                refs=list(item.get("refs", []) or []),
                style=str(item.get("style", "")),
                tags=list(item.get("tags", []) or []),
            )
            profs[prof.id] = prof
        speaker_map: dict[str, str] = {str(k): str(v) for k, v in (data.get("map", {}) or {}).items()}
        fallbacks: dict[str, str] = {str(k): str(v) for k, v in (data.get("fallbacks", {}) or {}).items()}
        return CharacterProfilesDB(profiles=profs, speaker_map=speaker_map, fallbacks=fallbacks)

    @staticmethod
    def _from_yaml_dict(data: Any) -> CharacterProfilesDB:
        if not isinstance(data, dict):
            raise ValueError("YAML profiles must be a mapping")
        defaults = data.get("defaults", {}) or {}
        default_engine = str(defaults.get("engine", "piper"))
        speakers_cfg = data.get("speakers", {}) or {}

        # build profiles
        profs: dict[str, Profile] = {}
        name_to_prof: dict[str, Profile] = {}

        def _mk_id(label: str) -> str:
            return normalize_speaker_name(label).replace(" ", "-") or "profile"

        narrator_prof: Profile | None = None
        for label, info in speakers_cfg.items():
            engine = str((info or {}).get("engine", default_engine))
            voice = str((info or {}).get("voice", ""))
            pid = _mk_id(str(label))
            prof = Profile(
                id=pid,
                label=str(label),
                engine=engine,
                voice=voice,
                refs=[],
                style=str(((info or {}).get("style") or {}).get("emotion", "")),
                tags=["narrator"] if normalize_speaker_name(str(label)) == normalize_speaker_name("Narrator") else [],
            )
            profs[pid] = prof
            name_to_prof[str(label)] = prof
            if prof.tags and "narrator" in prof.tags:
                narrator_prof = prof

        # speaker map with aliases
        speaker_map: dict[str, Profile] = {}
        for label, info in speakers_cfg.items():
            prof = name_to_prof[str(label)]
            speaker_map[str(label)] = prof
            for alias in (info or {}).get("aliases", []) or []:
                speaker_map[str(alias)] = prof

        # fallbacks: per engine to narrator if present
        fallbacks: dict[str, Profile] = {}
        if narrator_prof is not None:
            fallbacks[default_engine] = narrator_prof
        else:
            # any first profile
            if profs:
                fallbacks[default_engine] = next(iter(profs.values()))

        db = CharacterProfilesDB(profiles=profs)
        db.speaker_map = speaker_map
        db.fallbacks = fallbacks
        return db


# resolution & validation


def _resolve_with_reason(cfg: ProfileConfig, speaker: str) -> tuple[SpeakerProfile | None, str]:
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


def resolve_speaker_ex(cfg: ProfileConfig, speaker: str) -> tuple[SpeakerProfile | None, str]:
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


def resolve_with_reason(cfg: ProfileConfig, speaker: str) -> tuple[SpeakerProfile | None, str]:
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
            issues.append(f"speaker '{sp.name}' references unknown engine '{sp.engine}'")
        elif sp.voice not in cfg.voices.get(sp.engine, []):
            issues.append(f"speaker '{sp.name}' references unknown voice '{sp.voice}' for engine '{sp.engine}'")
        for alias in sp.aliases:
            norm = normalize_speaker_name(alias)
            if norm in canonical:
                issues.append(f"alias '{alias}' conflicts with existing speaker")
            if norm in alias_map:
                issues.append(f"alias '{alias}' claimed by '{alias_map[norm]}' and '{sp.name}'")
            alias_map[norm] = sp.name
        for eng, voice in sp.fallback.items():
            if eng not in cfg.voices:
                issues.append(f"speaker '{sp.name}' fallback engine '{eng}' unknown")
            elif voice not in cfg.voices[eng]:
                issues.append(f"speaker '{sp.name}' fallback voice '{voice}' unknown for engine '{eng}'")
    return issues
