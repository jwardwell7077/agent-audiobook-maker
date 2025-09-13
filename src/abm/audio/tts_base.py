"""Base classes for text-to-speech engines."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


class SynthesisError(RuntimeError):
    """Raised when synthesis fails."""


@dataclass(slots=True)
class TTSTask:
    """Data required to synthesize speech.

    Attributes:
        text: Text to synthesize.
        speaker: Speaker name.
        engine: Engine identifier.
        voice: Voice identifier.
        voice_path: Optional path to voice model.
        segments: Text segments (unused).
        out_path: Where synthesized audio will be written.
        words_per_minute: Target speech rate.
        style: Speaking style identifier.
    """

    text: str
    speaker: str
    engine: str
    voice: str
    voice_path: Path | None
    segments: Sequence[str]
    out_path: Path
    words_per_minute: int
    style: str


class TTSAdapter:
    """Abstract base class for TTS adapters."""

    def preload(self) -> None:  # pragma: no cover - interface
        """Load heavy resources or spawn processes."""

    def synth(self, task: TTSTask) -> Path:  # pragma: no cover - interface
        """Synthesize speech for a task.

        Args:
            task: Synthesis request.

        Returns:
            Path to synthesized WAV file.

        Raises:
            SynthesisError: If synthesis fails.
        """
        raise NotImplementedError
