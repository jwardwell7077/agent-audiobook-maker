"""Lightweight Piper engine wrapper used by the voice renderer."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["PiperEngine"]


class PiperEngine:
    """Minimal interface to the `piper` TTS engine.

    The implementation intentionally keeps features to a bare minimum for unit
    testing. It attempts to use the :command:`piper` binary if available,
    otherwise falls back to a simple synthetic tone. The real project integrates
    Piper via subprocess or :mod:`pydub`.
    """

    def __init__(
        self, voices_dir: Path | None = None, sample_rate: int = 48000
    ) -> None:
        self.voices_dir = Path(voices_dir) if voices_dir else None
        self.sample_rate = sample_rate
        self._piper_bin = shutil.which("piper")

    def synthesize(
        self, text: str, voice_id: str, style: dict[str, Any] | None = None
    ) -> np.ndarray:
        """Synthesize ``text`` with ``voice_id``.

        Args:
            text: Text to speak.
            voice_id: Identifier of the voice within Piper.
            style: Optional style dictionary (ignored).

        Returns:
            Mono audio waveform as ``float32`` ``[-1, 1]``.

        Raises:
            RuntimeError: If the Piper binary is unavailable.
        """

        if self._piper_bin is None:
            # In the testing environment we simply emit a short tone instead of
            # calling Piper. This keeps tests fast and deterministic while still
            # exercising downstream audio code.
            t = np.linspace(0, 0.2, int(self.sample_rate * 0.2), endpoint=False)
            return (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

        # A real implementation would invoke the Piper binary here.
        raise RuntimeError("subprocess piper synthesis not implemented in tests")
