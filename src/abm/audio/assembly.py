"""Utilities for stitching synthesized audio segments."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

__all__ = ["load_wav", "ensure_mono", "silence", "assemble"]


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    """Load a WAV file as mono ``float32`` samples.

    Args:
        path: Input WAV file path.

    Returns:
        Tuple of ``(samples, sample_rate)``.
    """

    data, sr = sf.read(path, dtype="float32")
    return data, int(sr)


def ensure_mono(y: np.ndarray) -> np.ndarray:
    """Collapse stereo signals to mono by averaging channels."""

    if y.ndim == 2 and y.shape[1] > 1:
        y = y.mean(axis=1)
    return y.astype(np.float32)


def silence(duration_ms: int, sr: int) -> np.ndarray:
    """Return a block of digital silence."""

    n = int(round(sr * duration_ms / 1000))
    return np.zeros(n, dtype=np.float32)


def assemble(
    span_paths: list[Path],
    pauses_ms: list[int],
    *,
    crossfade_ms: int = 15,
    sr_hint: int | None = None,
    allow_resample: bool = False,
) -> tuple[np.ndarray, int]:
    """Stitch a sequence of span WAVs with pauses and crossfades.

    Args:
        span_paths: Ordered list of WAV files to concatenate.
        pauses_ms: Silence duration to insert after each span; must have the
            same length as ``span_paths``.
        crossfade_ms: Duration of the equal-power crossfade at joins.
        sr_hint: If provided, enforce that all input files use this sample rate.
        allow_resample: Resample mismatched inputs if ``True`` and ``scipy`` is
            available; otherwise raise a ``ValueError``.

    Returns:
        Tuple ``(y, sr)`` where ``y`` is the assembled mono signal.
    """

    if len(span_paths) != len(pauses_ms):
        raise ValueError("pauses_ms must match span_paths length")
    if not span_paths:
        raise ValueError("No spans provided")

    def _maybe_resample(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
        if sr_in == sr_out:
            return y
        if not allow_resample:
            raise ValueError("Sample rate mismatch; pass allow_resample=True")
        try:  # pragma: no cover - optional dependency
            from scipy import signal  # type: ignore

            y = signal.resample_poly(y, sr_out, sr_in).astype(np.float32)
            return y
        except Exception as exc:  # pragma: no cover - scipy missing
            raise ValueError("Sample rate mismatch and scipy unavailable") from exc

    first, sr0 = load_wav(span_paths[0])
    sr = sr_hint or sr0
    first = _maybe_resample(first, sr0, sr)
    out = ensure_mono(first)

    crossfade_samples = int(round(sr * crossfade_ms / 1000))

    for idx in range(len(span_paths) - 1):
        pause = pauses_ms[idx]
        nxt, sr2 = load_wav(span_paths[idx + 1])
        nxt = _maybe_resample(nxt, sr2, sr)
        nxt = ensure_mono(nxt)

        if pause > 0:
            out = np.concatenate([out, silence(pause, sr), nxt])
            continue

        if (
            crossfade_samples > 0
            and len(out) >= crossfade_samples
            and len(nxt) >= crossfade_samples
        ):
            fade_out = np.sqrt(np.linspace(1.0, 0.0, crossfade_samples, endpoint=False))
            fade_in = np.sqrt(np.linspace(0.0, 1.0, crossfade_samples, endpoint=False))
            tail = out[-crossfade_samples:]
            head = nxt[:crossfade_samples]
            cross = tail * fade_out + head * fade_in
            out = np.concatenate(
                [out[:-crossfade_samples], cross, nxt[crossfade_samples:]]
            )
        else:
            out = np.concatenate([out, nxt])

    final_pause = pauses_ms[-1]
    if final_pause > 0:
        out = np.concatenate([out, silence(final_pause, sr)])

    out = np.clip(out, -1.0, 1.0).astype(np.float32)
    return out, sr
