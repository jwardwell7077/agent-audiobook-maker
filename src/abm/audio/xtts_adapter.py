"""Coqui XTTS v2 adapter (GPU if available).

- Uses the `TTS` library when installed. Falls back to a dry-run mode if
  `ABM_XTTS_DRYRUN=1` or the library is not present.
- Embeddings are cached per `profile_id` for speed.

Dry-run writes a short sine wave (so tests don't need GPUs/models).
"""

from __future__ import annotations

import math
import os
import re
import wave
from pathlib import Path
from typing import Any

from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import SynthesisError, TTSAdapter, TTSTask


def _write_sine_wav(
    path: Path, duration_ms: int = 300, sr: int = 22050, freq: float = 220.0
) -> None:
    """Write a short sine wave WAV (PCM 16-bit mono) for dry runs."""
    nframes = int(sr * (duration_ms / 1000.0))
    amp = 0.2  # keep headroom
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for n in range(nframes):
            val = int(amp * 32767 * math.sin(2 * math.pi * freq * (n / sr)))
            frames += val.to_bytes(2, byteorder="little", signed=True)
        wf.writeframes(frames)


class XTTSAdapter(TTSAdapter):
    """XTTS v2 adapter using the Coqui `TTS` library.

    Args:
        model_name: TTS model name (default: XTTS v2 canonical id).
        device: "cuda" or "cpu".
        denoiser_strength: Optional denoiser parameter forwarded to TTS.

    Notes:
        - Embedding cache keyed by `profile_id` if provided.
        - If the `TTS` library is missing or `ABM_XTTS_DRYRUN=1`, a sine WAV
          is written instead (for tests).
    """

    DEFAULT_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(
        self,
        model_name: str | None = None,
        *,
        device: str = "cuda",
        denoiser_strength: float | None = None,
    ) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.denoiser_strength = denoiser_strength
        self._dryrun = os.environ.get("ABM_XTTS_DRYRUN", "") == "1"
        self._tts: Any | None = None  # lazy import; Any to avoid hard dependency
        self._emb_cache: dict[str, tuple[Any, Any]] = {}

    # ---------------------- helpers ---------------------- #

    def preload(self) -> None:
        """Load the XTTS model unless in dry-run mode."""
        if self._dryrun:
            return
        try:
            from TTS.api import TTS  # type: ignore
        except Exception as exc:  # pragma: no cover - exercised in real env
            raise SynthesisError(
                "Coqui TTS not installed. Set ABM_XTTS_DRYRUN=1 for tests or install `TTS`."
            ) from exc
        self._tts = TTS(self.model_name).to(self.device)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences using a simple regex."""
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p for p in parts if p]

    def _speaker_latents(self, task: TTSTask) -> dict[str, Any]:
        """Return cached speaker/gpt latents for cloning."""
        if not task.refs:
            return {}
        if self._tts is None:
            raise SynthesisError("XTTS model is not loaded. Call preload() first.")
        key = task.profile_id or "|".join(map(str, task.refs))
        if key not in self._emb_cache:
            gpt_latent, speaker_embedding = self._tts.get_conditioning_latents(
                audio_path=task.refs
            )
            self._emb_cache[key] = (gpt_latent, speaker_embedding)
        gpt_latent, speaker_embedding = self._emb_cache[key]
        return {"gpt_cond_latent": gpt_latent, "speaker_embedding": speaker_embedding}

    # ---------------------- main API ---------------------- #

    def synth(self, task: TTSTask) -> Path:
        """Synthesize speech using XTTS or write a sine wave in dry-run."""
        task.out_path.parent.mkdir(parents=True, exist_ok=True)

        if self._dryrun:
            _write_sine_wav(task.out_path)
            return task.out_path

        if self._tts is None:
            raise SynthesisError("XTTS model is not loaded. Call preload() first.")

        text = task.text.strip()
        if not text:
            _write_sine_wav(task.out_path, duration_ms=50, freq=0.0)
            return task.out_path

        import numpy as np  # Imported here to keep deps optional for tests

        sentences = self._split_sentences(text)
        speaker_args = self._speaker_latents(task)
        tts_kwargs: dict[str, Any] = {"language": task.language or "en"}
        if self.denoiser_strength is not None:
            tts_kwargs["denoiser_strength"] = self.denoiser_strength
        sr = getattr(self._tts.synthesizer, "output_sample_rate", 22050)
        chunks: list[np.ndarray] = []
        for idx, sent in enumerate(sentences):
            wav = self._tts.tts(text=sent, **speaker_args, **tts_kwargs)
            wav_arr = np.asarray(wav, dtype=np.float32)
            chunks.append(wav_arr)
            if task.pause_ms and idx < len(sentences) - 1:
                pad = np.zeros(int(sr * task.pause_ms / 1000), dtype=np.float32)
                chunks.append(pad)

        if not chunks:
            _write_sine_wav(task.out_path, duration_ms=50, freq=0.0)
            return task.out_path

        audio = np.concatenate(chunks)
        int_samples = np.clip(audio, -1.0, 1.0)
        int_samples = (int_samples * 32767).astype("<i2")
        with wave.open(str(task.out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(int_samples.tobytes())

        if not task.out_path.exists() or task.out_path.stat().st_size < 200:
            raise SynthesisError("XTTS produced no output or an empty file.")
        return task.out_path


# Auto-register
EngineRegistry.register("xtts", lambda **kw: XTTSAdapter(**kw))
