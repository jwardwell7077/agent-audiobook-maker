"""Character profile database utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import jsonschema
except Exception:  # pragma: no cover - graceful fallback
    jsonschema = None  # type: ignore
    logging.getLogger(__name__).warning(
        "jsonschema not available; profile validation skipped"
    )


@dataclass
class Profile:
    """Description of a character's TTS profile.

    Attributes:
        id: Unique profile identifier.
        label: Human-friendly name.
        engine: TTS engine key.
        voice: Voice identifier for the engine.
        refs: Reference audio filenames.
        style: Optional style token for the engine.
        gender: Gender descriptor.
        age: Age descriptor.
        accent: Accent descriptor.
        notes: Freeform notes.
        tags: Arbitrary tags used for heuristics.
    """

    id: str
    label: str
    engine: str
    voice: str
    refs: list[str]
    style: str = ""
    gender: str | None = None
    age: str | None = None
    accent: str | None = None
    notes: str | None = None
    tags: list[str] = field(default_factory=list)


PROFILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "label": {"type": "string"},
        "engine": {"type": "string"},
        "voice": {"type": "string"},
        "refs": {"type": "array", "items": {"type": "string"}},
        "style": {"type": "string"},
        "gender": {"type": ["string", "null"]},
        "age": {"type": ["string", "null"]},
        "accent": {"type": ["string", "null"]},
        "notes": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "label", "engine", "voice", "refs", "style"],
}


DB_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "profiles": {"type": "array", "items": PROFILE_SCHEMA},
        "map": {"type": "object", "additionalProperties": {"type": "string"}},
        "fallbacks": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
    },
    "required": ["profiles"],
}


class CharacterProfilesDB:
    """In-memory database of character profiles."""

    def __init__(
        self,
        profiles: dict[str, Profile],
        speaker_map: dict[str, str] | None = None,
        fallbacks: dict[str, str] | None = None,
    ) -> None:
        self.profiles = profiles
        self.speaker_map = speaker_map or {}
        self.fallbacks = fallbacks or {}

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> CharacterProfilesDB:
        """Load profiles from JSON file."""

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        db = cls(
            {p["id"]: Profile(**p) for p in data.get("profiles", [])},
            data.get("map", {}),
            data.get("fallbacks", {}),
        )
        issues = db.validate(data)
        if issues:
            raise ValueError("; ".join(issues))
        return db

    # ------------------------------------------------------------------
    def save(self, path: Path) -> None:
        """Write profiles to JSON file."""

        data = {
            "profiles": [asdict(p) for p in self.profiles.values()],
            "map": self.speaker_map,
            "fallbacks": self.fallbacks,
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    # ------------------------------------------------------------------
    def validate(self, data: dict[str, Any] | None = None) -> list[str]:
        """Validate the database structure.

        Returns a list of human-readable issues. If :mod:`jsonschema` is
        available, it is used; otherwise a few structural checks are performed.
        """

        if data is None:
            data = {
                "profiles": [asdict(p) for p in self.profiles.values()],
                "map": self.speaker_map,
                "fallbacks": self.fallbacks,
            }

        issues: list[str] = []
        if jsonschema is not None:  # pragma: no cover - straightforward
            validator = jsonschema.Draft7Validator(DB_SCHEMA)
            issues.extend(err.message for err in validator.iter_errors(data))
            return issues

        profiles = data.get("profiles")
        if not isinstance(profiles, list):
            issues.append("profiles must be a list")
            profiles = []
        required = ["id", "label", "engine", "voice", "refs", "style"]
        ids = set()
        for p in profiles:
            issues.extend(f"profile missing {k}: {p}" for k in required if k not in p)
            ids.add(p.get("id"))
        for spk, pid in data.get("map", {}).items():
            if pid not in ids:
                issues.append(
                    f"map references unknown profile '{pid}' for speaker '{spk}'"
                )
        for eng, pid in data.get("fallbacks", {}).items():
            if pid not in ids:
                issues.append(
                    f"fallback for '{eng}' references unknown profile '{pid}'"
                )
        return issues

    # ------------------------------------------------------------------
    def get(self, profile_id: str) -> Profile:
        """Return profile by identifier."""

        return self.profiles[profile_id]

    # ------------------------------------------------------------------
    def by_speaker(self, speaker: str) -> Profile | None:
        """Return profile mapped to ``speaker`` if any."""

        pid = self.speaker_map.get(speaker)
        if pid:
            return self.profiles.get(pid)
        return None

    # ------------------------------------------------------------------
    def fallback(self, engine: str) -> Profile | None:
        """Return the fallback narrator profile for ``engine`` if defined."""

        pid = self.fallbacks.get(engine)
        if pid:
            return self.profiles.get(pid)
        return None


__all__ = ["Profile", "CharacterProfilesDB", "PROFILE_SCHEMA"]
