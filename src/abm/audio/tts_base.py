"""Base interfaces and dataclasses for TTS adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SynthesisError(RuntimeError):
    """Raised when a TTS engine fails to synthesize audio."""


@dataclass(frozen=True)
class TTSTask:
    """A single text-to-speech synthesis job.

    Attributes:
        text: Text content to synthesize (plain text; pre-normalized).
        speaker: Canonical speaker name (e.g., "Quinn", "Narrator").
        engine: Engine identifier (e.g., "piper", "xtts").
        voice: Engine-specific voice/model name (optional for cloning engines).
        profile_id: Logical id used for caching embeddings (e.g., "quinn_v1").
        refs: Reference WAV file paths for voice cloning (may be empty).
        out_path: Destination WAV file path (PCM 16-bit recommended).
        pause_ms: Recommended pause length after this span, in milliseconds.
        style: Freeform style tags (e.g., "calm, authoritative").
    """

    text: str
    speaker: str
    engine: str
    voice: str | None
    profile_id: str | None
    refs: list[str]
    out_path: Path
    pause_ms: int
    style: str


class TTSAdapter:
    """Abstract base class for all TTS engine adapters.

    Subclasses must implement :meth:`preload` and :meth:`synth`.
    """

    def preload(self) -> None:
        """Load models, start subprocesses, or warm caches.

        Implementations should be idempotent. Calling ``preload()`` multiple times
        must not have side effects other than ensuring the adapter is ready.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """

        raise NotImplementedError

    def synth(self, task: TTSTask) -> Path:
        """Synthesize speech and write a WAV file to ``task.out_path``.

        Args:
            task: The synthesis request containing text, output path, and voice info.

        Returns:
            The absolute path to the written WAV file.

        Raises:
            SynthesisError: If the engine fails to render audio or write the file.
            NotImplementedError: If the subclass does not override this method.
        """

        raise NotImplementedError
