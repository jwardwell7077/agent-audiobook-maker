from __future__ import annotations
import numpy as np, torch
import torchaudio
import soundfile as sf  # noqa: F401 - parity with other engines
from dataclasses import dataclass
from transformers import AutoTokenizer
from parler_tts import ParlerTTSForConditionalGeneration


@dataclass
class ParlerConfig:
    model_name: str = "parler-tts/parler-tts-mini-v1"
    device: str = "auto"  # "auto"|"cuda"|"cpu"
    dtype: str = "auto"   # "auto"|"float16"|"bfloat16"


class ParlerEngine:
    """Minimal wrapper around Parler-TTS models."""

    def __init__(self, cfg: ParlerConfig | None = None):
        self.cfg = cfg or ParlerConfig()
        device = (
            "cuda:0" if self.cfg.device == "auto" and torch.cuda.is_available()
            else ("cpu" if self.cfg.device == "auto" else self.cfg.device)
        )
        self.device = torch.device(device)
        try:
            self.model = ParlerTTSForConditionalGeneration.from_pretrained(
                self.cfg.model_name
            ).to(self.device)
            self.tok = AutoTokenizer.from_pretrained(self.cfg.model_name)
        except Exception as exc:  # pragma: no cover - initialization
            raise RuntimeError(
                f"failed to load Parler-TTS model {self.cfg.model_name}"
            ) from exc
        self.native_sr = int(getattr(self.model.config, "sampling_rate", 24000))
        if self.cfg.dtype in ("float16", "bfloat16") and self.device.type == "cuda":
            dtype = torch.float16 if self.cfg.dtype == "float16" else torch.bfloat16
            self.model = self.model.to(dtype=dtype)
        self.target_sr = 48000

    def synthesize(
        self,
        text: str,
        voice_id: str,
        style: dict[str, float] | None = None,
        *,
        description: str | None = None,
        seed: int | None = None,
    ) -> np.ndarray:
        """Synthesize ``text`` with ``voice_id`` and optional ``description``."""

        if seed is not None:
            torch.manual_seed(int(seed))
        desc = f"{voice_id}'s voice {description or 'is neutral and very clear.'}"
        try:
            input_ids = self.tok(desc, return_tensors="pt").input_ids.to(self.device)
            prompt_ids = self.tok(text, return_tensors="pt").input_ids.to(self.device)
            with torch.inference_mode():
                audio = self.model.generate(
                    input_ids=input_ids, prompt_input_ids=prompt_ids
                )
        except Exception as exc:  # pragma: no cover - generation errors
            raise RuntimeError("parler synthesis failed") from exc
        wav = audio.squeeze().detach().cpu().float()
        if self.native_sr != self.target_sr:
            wav = torchaudio.functional.resample(wav, self.native_sr, self.target_sr)
        return wav.numpy().astype(np.float32)
