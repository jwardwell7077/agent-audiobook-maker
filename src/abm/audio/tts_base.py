"""Base classes for text-to-speech adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SynthesisError(RuntimeError):
    """Error raised when synthesis fails."""


@dataclass
class TTSTask:
    """Description of a synthesis request.

    Attributes:
        text: Text to speak.
        voice: Voice identifier for logs.
        engine_id: Engine identifier (e.g., "xtts").
        language: Optional language code.
        profile_id: Optional speaker profile identifier for caching.
        out_path: Output WAV path.
        refs: Optional list of reference WAV paths for cloning.
        pause_ms: Optional pause inserted between chunks.
        style: Optional style tag.
    """

    text: str
    voice: str
    engine_id: str
    language: str | None
    profile_id: str | None
    out_path: Path
    refs: list[Path] | None = None
    pause_ms: int | None = None
    style: str | None = None


class TTSAdapter(Protocol):
    """Protocol for TTS adapters."""

    def preload(self) -> None:
        """Load models into memory if necessary."""

    def synth(self, task: TTSTask) -> Path:
        """Perform synthesis and return the output path."""
        ...
