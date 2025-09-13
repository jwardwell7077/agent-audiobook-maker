"""Profile configuration and utilities."""

# isort: skip_file

from __future__ import annotations

# ruff: noqa: I001
from abm.profiles.character_profiles import (
    ProfileConfig,
    SpeakerProfile,
    Style,
    available_voices,
    load_profiles,
    normalize_speaker_name,
    resolve_speaker,
    resolve_speaker_ex,
    resolve_with_reason,
    validate_profiles,
)

__all__ = [
    "Style",
    "SpeakerProfile",
    "ProfileConfig",
    "load_profiles",
    "validate_profiles",
    "normalize_speaker_name",
    "resolve_speaker_ex",
    "resolve_with_reason",
    "resolve_speaker",
    "available_voices",
]
