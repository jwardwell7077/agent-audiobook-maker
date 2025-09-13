"""Piper TTS adapter (CPU).

This adapter manages a persistent ``piper`` subprocess. Each synthesis task
writes text to ``stdin`` and captures a WAV stream from ``stdout``. For unit
tests or environments without Piper installed, enable dry-run mode via the
environment variable ``ABM_PIPER_DRYRUN=1`` to generate a short silent WAV
instead.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from abm.audio.engine_registry import EngineRegistry
from abm.audio.tts_base import SynthesisError, TTSAdapter, TTSTask


def _write_silence_wav(path: Path, duration_ms: int = 250, sr: int = 22050) -> None:
    """Write a short silence WAV (PCM 16-bit mono) for dry runs.

    Args:
        path: Output file path.
        duration_ms: Length in milliseconds.
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
    """Adapter that streams to a long-lived ``piper`` process.

    Attributes:
        voice: Piper voice identifier, e.g., ``en_US-ryan-medium``.
        binary: Piper executable name/path. Defaults to ``piper``.
        quiet: Reduce CLI output when possible.
    """

    def __init__(
        self, voice: str, *, binary: str | None = None, quiet: bool = True
    ) -> None:
        self.voice = voice
        self.binary = binary or os.environ.get("ABM_PIPER_BIN", "piper")
        self.quiet = quiet
        self._dryrun = os.environ.get("ABM_PIPER_DRYRUN", "") == "1"
        self._proc: subprocess.Popen[bytes] | None = None

    def preload(self) -> None:
        """Start the Piper subprocess if available."""
        if self._dryrun:
            return
        if shutil.which(self.binary) is None:
            raise SynthesisError(
                "Piper binary not found. Set ABM_PIPER_DRYRUN=1 for tests or install Piper."
            )
        cmd = [self.binary, "--voice", self.voice]
        if self.quiet:
            cmd.insert(1, "--quiet")
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def synth(self, task: TTSTask) -> Path:
        """Synthesize speech using the persistent Piper process.

        Args:
            task: Synthesis request.

        Returns:
            Path to the written WAV file.

        Raises:
            SynthesisError: If Piper fails or outputs unexpected audio.
        """
        if self._dryrun:
            _write_silence_wav(task.out_path)
            return task.out_path
        if not self._proc or self._proc.poll() is not None:
            raise SynthesisError("Piper process not running. Call preload() first.")

        try:
            self._proc.stdin.write((task.text.strip() + "\n").encode("utf-8"))
            self._proc.stdin.flush()
        except Exception as exc:  # pragma: no cover - process I/O
            raise SynthesisError(f"Failed to send text to Piper: {exc}") from exc

        header = self._proc.stdout.read(44)
        if len(header) != 44 or not header.startswith(b"RIFF"):
            err = self._proc.stderr.read().decode("utf-8", errors="ignore").strip()
            raise SynthesisError(f"Piper produced invalid WAV header: {err}")
        data_len = struct.unpack("<I", header[40:44])[0]
        audio = self._proc.stdout.read(data_len)
        if len(audio) != data_len:
            raise SynthesisError("Incomplete audio data from Piper")

        sampwidth = struct.unpack("<H", header[34:36])[0]
        framerate = struct.unpack("<I", header[24:28])[0]
        if sampwidth != 16:
            raise SynthesisError("Piper output is not 16-bit PCM")
        if framerate not in (22050, 24000):
            raise SynthesisError(f"Unsupported sample rate: {framerate}")

        task.out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(task.out_path, "wb") as f:
            f.write(header + audio)
        return task.out_path

    def __del__(self) -> None:  # pragma: no cover - cleanup
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._proc.kill()


EngineRegistry.register("piper", lambda **kw: PiperAdapter(**kw))
