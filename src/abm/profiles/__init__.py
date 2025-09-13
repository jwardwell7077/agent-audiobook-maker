"""Profile configuration and utilities."""

from __future__ import annotations

from abm.profiles.character_profiles import (
    ProfileConfig,
    SpeakerProfile,
    Style,
    available_voices,
    load_profiles,
    normalize_speaker_name,
    resolve_speaker,
    validate_profiles,
)

__all__ = [
    "Style",
    "SpeakerProfile",
    "ProfileConfig",
    "load_profiles",
    "validate_profiles",
    "normalize_speaker_name",
    "resolve_speaker",
    "available_voices",
]
