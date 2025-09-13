"""Coqui XTTS v2 adapter (GPU preferred, CPU fallback).

- Uses the `TTS` library at runtime if available.
- Supports dry-run via env ABM_XTTS_DRYRUN=1 to emit a short sine WAV for tests.

Registration happens via :func:`abm.audio.register_builtins` under the key
``"xtts"``.
"""

from __future__ import annotations

import math
import os
import wave
from pathlib import Path
from typing import Any

from abm.audio.tts_base import SynthesisError, TTSAdapter, TTSTask


def _write_sine_wav(
    path: Path, duration_ms: int = 300, sr: int = 22050, freq: float = 440.0
) -> None:
    """Write a short 16-bit PCM mono sine WAV for dry-run tests."""
    nframes = int(sr * (duration_ms / 1000.0))
    amp = 0.2
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for n in range(nframes):
            val = int(amp * 32767 * math.sin(2 * math.pi * freq * (n / sr)))
            frames += val.to_bytes(2, "little", signed=True)
        wf.writeframes(frames)


class XTTSAdapter(TTSAdapter):
    """Adapter for Coqui XTTS v2 (speaker cloning).

    Args:
        model_name: Model identifier. Defaults to ``DEFAULT_MODEL`` or
            ``ABM_XTTS_MODEL`` env var if set.
        device: Execution device. Defaults to ``ABM_XTTS_DEVICE`` env var or
            ``'cuda'``.
        denoiser_strength: Optional denoiser parameter passed through to TTS.

    Attributes:
        model_name: Resolved model identifier.
        device: Chosen device.
        denoiser_strength: Denoiser strength if used.
        _tts: Internal TTS object (lazy).
        _dryrun: If True, writes a sine WAV instead of calling TTS.
    """

    DEFAULT_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(
        self,
        model_name: str | None = None,
        *,
        device: str | None = None,
        denoiser_strength: float | None = None,
    ) -> None:
        env_model = os.environ.get("ABM_XTTS_MODEL")
        env_device = os.environ.get("ABM_XTTS_DEVICE")
        self.model_name = model_name or env_model or self.DEFAULT_MODEL
        self.device = device or env_device or "cuda"
        self.denoiser_strength = denoiser_strength
        self._dryrun = os.environ.get("ABM_XTTS_DRYRUN", "") == "1"
        self._tts: Any | None = None

    def preload(self) -> None:
        """Load the XTTS model unless running in dry-run mode."""
        if self._dryrun:
            return
        try:
            from TTS.api import TTS  # type: ignore
        except Exception as exc:  # pragma: no cover (covered in real env)
            raise SynthesisError(
                "Coqui TTS not installed. Install `TTS` or set ABM_XTTS_DRYRUN=1 for tests."
            ) from exc
        self._tts = TTS(self.model_name).to(self.device)

    def _speaker_kwargs(self, task: TTSTask) -> dict[str, Any]:
        """Prepare speaker cloning arguments for XTTS."""
        kwargs: dict[str, Any] = {}
        if task.refs:
            kwargs["speaker_wav"] = task.refs  # list of reference wavs
        return kwargs

    def synth(self, task: TTSTask) -> Path:
        """Synthesize using XTTS or write a sine WAV under dry-run.

        Args:
            task: The synthesis request.

        Returns:
            Path to the rendered WAV file.

        Raises:
            SynthesisError: If the model isn't loaded or synthesis fails.
        """
        task.out_path.parent.mkdir(parents=True, exist_ok=True)

        if self._dryrun:
            _write_sine_wav(task.out_path)
            return task.out_path

        if self._tts is None:
            raise SynthesisError("XTTS model not loaded. Call preload() first.")

        text = task.text.strip()
        if not text:
            _write_sine_wav(task.out_path, duration_ms=50)
            return task.out_path

        speaker_args = self._speaker_kwargs(task)
        try:
            # Render directly to file; language fixed to English for this project.
            self._tts.tts_to_file(
                text=text, file_path=str(task.out_path), language="en", **speaker_args
            )
        except Exception as exc:  # pragma: no cover (covered in real env)
            raise SynthesisError(f"XTTS synthesis failed: {exc}") from exc

        if not task.out_path.exists() or task.out_path.stat().st_size < 200:
            raise SynthesisError("XTTS produced an empty or missing file.")
        return task.out_path
