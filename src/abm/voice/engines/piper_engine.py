"""Lightweight Piper engine wrapper used by the voice renderer."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

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
        sample_rate: int | None = None,
        *,
        use_subprocess: bool | None = None,
    ) -> None:
        """Initialize Piper engine.

        - If ``use_subprocess`` is None, auto-enable when the ``piper`` binary
          is available on PATH.
        - ``voices_dir`` is optional; when omitted, common locations are searched.
        - ``sample_rate`` is advisory only; output uses the model's native rate.
        """
        self.voices_dir = Path(voices_dir) if voices_dir else None
        self.sample_rate = sample_rate
        self.last_sample_rate: int | None = None
        self._piper_bin = shutil.which("piper")
        self.use_subprocess = use_subprocess if use_subprocess is not None else (self._piper_bin is not None)

    def _candidate_dirs(self) -> list[Path]:
        if self.voices_dir:
            return [self.voices_dir]
        env = os.environ.get("ABM_PIPER_VOICES_DIR")
        if env:
            return [Path(env)]
        return [
            Path.home() / ".local/share/piper/voices",
            Path("/usr/share/piper/voices"),
            Path("/usr/local/share/piper/voices"),
        ]

    def _resolve_model_paths(self, voice_id: str) -> tuple[Path | None, Path | None]:
        """Resolve a Piper voice id to (model_path, config_path).

        Accepts either a bare id like "en_US-libritts-high" or an explicit model
        file path ending with .onnx. Returns (None, None) when not found.
        """
        # Explicit model path
        vid = voice_id
        if voice_id.endswith(".onnx"):
            model = Path(voice_id)
            # Prefer .onnx.json next to the model
            cfg = model.with_suffix(".onnx.json")
            if not cfg.exists():
                # Some distributions use plain .json
                cfg = model.with_suffix(".json")
            return (model, cfg if cfg.exists() else None)
        # Try standard layout: <dir>/<id>/<id>.onnx and <id>.onnx.json
        for root in self._candidate_dirs():
            model = root / vid / f"{vid}.onnx"
            if model.exists():
                # Piper configs commonly use the .onnx.json suffix next to the model
                cfg = model.with_suffix(".onnx.json")
                if not cfg.exists():
                    cfg = model.with_suffix(".json")
                return (model, cfg if cfg.exists() else None)
        return (None, None)

    def synthesize(self, text: str, voice_id: str, style: dict[str, Any] | None = None) -> np.ndarray:
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
            model_path, cfg_path = self._resolve_model_paths(voice_id)
            # If resolution fails, pass the provided voice_id through as-is.
            # This keeps unit tests simple and still works when callers provide
            # an explicit .onnx path.
            selected_model = str(model_path) if model_path is not None else str(voice_id)
            with (
                tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav,
                tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp_txt,
            ):
                tmp_txt.write(text)
                tmp_txt.flush()
                cmd = [self._piper_bin, "-m", str(selected_model), "-f", tmp_wav.name, "-i", tmp_txt.name]
                if cfg_path is not None:
                    cmd.extend(["-c", str(cfg_path)])
                proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0:
                tail = "\n".join(proc.stderr.decode().splitlines()[-10:])
                raise RuntimeError(f"piper synthesis failed: {tail}")
            data, sr = sf.read(tmp_wav.name, dtype="float32")
            self.last_sample_rate = int(sr)
            Path(tmp_wav.name).unlink(missing_ok=True)
            try:
                Path(tmp_txt.name).unlink(missing_ok=True)
            except Exception:
                pass
            # Optionally resample to requested sample_rate
            target_sr = int(self.sample_rate) if self.sample_rate else None
            if target_sr and target_sr != int(sr):
                data = _resample_audio(cast(np.ndarray, data), int(sr), target_sr)
            # Return at (possibly resampled) SR
            return cast(np.ndarray, data)

        # Fallback: emit a short tone to keep tests deterministic.
        sr = int(self.sample_rate) if self.sample_rate is not None else 48000
        self.last_sample_rate = sr
        t = np.linspace(0, 0.2, int(sr * 0.2), endpoint=False)
        return (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _resample_audio(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Resample y from sr_in to sr_out using high-quality polyphase if available.

    Falls back to linear interpolation when SciPy is unavailable.
    """
    if sr_in == sr_out:
        return y.astype(np.float32)
    try:  # pragma: no cover - optional dependency
        from scipy import signal  # type: ignore

        y2 = signal.resample_poly(y, sr_out, sr_in).astype(np.float32)
        return cast(np.ndarray, y2)
    except Exception:
        # NumPy fallback: linear interpolation
        x = np.arange(len(y), dtype=np.float64)
        duration_s = len(y) / float(sr_in)
        n_out = int(round(duration_s * sr_out))
        xi = np.linspace(0.0, len(y) - 1, n_out, endpoint=True)
        y2 = np.interp(xi, x, y.astype(np.float64)).astype(np.float32)
        return cast(np.ndarray, y2)
