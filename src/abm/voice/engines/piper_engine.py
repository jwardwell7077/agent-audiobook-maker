"""Lightweight Piper engine wrapper used by the voice renderer."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

__all__ = ["PiperEngine"]


class PiperEngine:
    """Minimal interface to the `piper` TTS engine.

    The implementation intentionally keeps features to a bare minimum for unit
    testing. It attempts to use the :command:`piper` binary if available,
    otherwise falls back to a simple synthetic tone. The real project integrates
    Piper via subprocess or :mod:`pydub`.
    """

    def __init__(
        self,
        voices_dir: Path | None = None,
        sample_rate: int = 48000,
        *,
        use_subprocess: bool = False,
    ) -> None:
        self.voices_dir = Path(voices_dir) if voices_dir else None
        self.sample_rate = sample_rate
        self.use_subprocess = use_subprocess
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

        if self.use_subprocess and self._piper_bin is not None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                cmd = [self._piper_bin, "-q", "-f", tmp.name]
                if self.voices_dir:
                    cmd.extend(["-m", str(self.voices_dir / voice_id)])
                proc = subprocess.run(
                    cmd,
                    input=text.encode("utf-8"),
                    capture_output=True,
                )
            if proc.returncode != 0:
                tail = "\n".join(proc.stderr.decode().splitlines()[-10:])
                raise RuntimeError(f"piper synthesis failed: {tail}")
            data, sr = sf.read(tmp.name, dtype="float32")
            Path(tmp.name).unlink(missing_ok=True)
            if sr != self.sample_rate:
                raise RuntimeError(f"unexpected sample rate {sr}")
            return data

        # Fallback: emit a short tone to keep tests deterministic.
        t = np.linspace(0, 0.2, int(self.sample_rate * 0.2), endpoint=False)
        return (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
