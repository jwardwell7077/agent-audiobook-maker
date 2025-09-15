"""Piper TTS adapter (CLI-based, CPU-friendly).

Supports a dry-run mode (env ABM_PIPER_DRYRUN=1) that writes a short silence WAV
so unit tests can run without Piper installed.

Registration happens via :func:`abm.audio.register_builtins` under the key
``"piper"``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from abm.audio.tts_base import SynthesisError, TTSAdapter, TTSTask


def _write_silence_wav(path: Path, duration_ms: int = 250, sr: int = 22050) -> None:
    """Write a short 16-bit PCM mono silence WAV.

    Args:
        path: Output file path.
        duration_ms: Duration of the silence in milliseconds.
        sr: Sample rate in Hz.
    """
    nframes = int(sr * (duration_ms / 1000.0))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * nframes)


class PiperAdapter(TTSAdapter):
    """Adapter that calls the `piper` CLI per synthesis request.

    Attributes:
        voice: Piper voice identifier (e.g., 'en_US-ryan-medium').
        binary: Piper executable or full path. Defaults to 'piper'.
        quiet: Whether to request reduced CLI output.
        _dryrun: Internal flag to emit silence WAVs instead of calling Piper.
        _available: Cached boolean indicating if the Piper binary is found.
    """

    def __init__(self, voice: str | None = None, *, binary: str | None = None, quiet: bool = True) -> None:
        """Initialize the Piper adapter.

        Args:
            voice: Optional default Piper voice identifier. If omitted, each
                TTSTask must provide ``task.voice``.
            binary: Binary name or absolute path to the Piper executable.
            quiet: Suppress CLI output where supported.
        """
        self.voice = voice
        self.binary = binary or os.environ.get("ABM_PIPER_BIN", "piper")
        self.quiet = quiet
        self._dryrun = os.environ.get("ABM_PIPER_DRYRUN", "") == "1"
        self._available: bool | None = None

    # Adapter version string used by TTSManager cache keys. Bump this when
    # changing CLI invocation, normalization, or output-affecting behavior
    # to avoid reusing stale cache entries.
    def version(self) -> str:  # pragma: no cover - simple constant
        return "piper-adapter-2"

    def preload(self) -> None:
        """Check the Piper binary availability (unless in dry-run)."""
        if self._dryrun:
            self._available = False
            return
        bin_path = shutil.which(self.binary or "piper")
        self._available = bin_path is not None

    def _candidate_dirs(self) -> list[Path]:
        env = os.environ.get("ABM_PIPER_VOICES_DIR")
        if env:
            return [Path(env)]
        return [
            Path.home() / ".local/share/piper/voices",
            Path("/usr/share/piper/voices"),
            Path("/usr/local/share/piper/voices"),
        ]

    def _resolve_model_paths(self, voice_id: str) -> tuple[Path | None, Path | None]:
        """Resolve a Piper voice id to (model_path, config_path)."""
        if voice_id.endswith(".onnx"):
            model = Path(voice_id)
            cfg = model.with_suffix(".onnx.json")
            if not cfg.exists():
                cfg = model.with_suffix(".json")
            return (model, cfg if cfg.exists() else None)
        for root in self._candidate_dirs():
            model = root / voice_id / f"{voice_id}.onnx"
            if model.exists():
                cfg = model.with_suffix(".onnx.json")
                if not cfg.exists():
                    cfg = model.with_suffix(".json")
                return (model, cfg if cfg.exists() else None)
        return (None, None)

    def _build_cmd(self, voice_id: str, text_file: Path, out_file: Path) -> list[str]:
        """Build the Piper CLI command line."""
        model, cfg = self._resolve_model_paths(voice_id)
        model_arg = str(model) if model is not None else str(voice_id)
        bin_exe = self.binary or "piper"
        cmd: list[str] = [bin_exe, "-m", model_arg, "-i", str(text_file), "-f", str(out_file)]
        if cfg is not None:
            cmd.extend(["-c", str(cfg)])
        return cmd

    def synth(self, task: TTSTask) -> Path:
        """Synthesize speech using Piper or dry-run fallback.

        Args:
            task: The synthesis request.

        Returns:
            Path to the written WAV file.

        Raises:
            SynthesisError: If Piper is missing (non-dry-run) or the process fails.
        """
        # Dry run → produce silence WAV
        if self._dryrun:
            _write_silence_wav(task.out_path)
            return task.out_path

        # Real run → require binary
        if not self._available:
            raise SynthesisError("Piper binary not found. Install Piper or set ABM_PIPER_DRYRUN=1 for tests.")

        task.out_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine voice to use for this task
        voice_id = (task.voice or self.voice or "").strip()
        if not voice_id:
            raise SynthesisError(
                "Piper voice not specified. Provide TTSTask.voice or set a default when creating the adapter."
            )
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
            tf.write(task.text)
            tf.flush()
            text_file = Path(tf.name)

        try:
            cmd = self._build_cmd(voice_id, text_file, task.out_path)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired as exc:
                raise SynthesisError(f"Piper timed out after {exc.timeout}s") from exc
            if proc.returncode != 0 or not task.out_path.exists() or task.out_path.stat().st_size < 64:
                err = (proc.stderr or proc.stdout or "").strip() or "unknown error"
                raise SynthesisError(f"Piper failed (rc={proc.returncode}): {err}")
            return task.out_path
        finally:
            try:
                text_file.unlink(missing_ok=True)
            except Exception:
                pass
