"""Numpy-based audio concatenation helpers."""

from __future__ import annotations

import numpy as np

__all__ = ["equal_power_crossfade", "micro_fade"]


def equal_power_crossfade(
    a: np.ndarray, b: np.ndarray, sr: int, crossfade_ms: int
) -> np.ndarray:
    """Join two mono signals with an equal-power crossfade.

    Args:
        a: First signal ``[-1, 1]``.
        b: Second signal ``[-1, 1]``.
        sr: Sample rate in Hz.
        crossfade_ms: Duration of the crossfade in milliseconds.

    Returns:
        Concatenated signal.
    """

    if crossfade_ms <= 0:
        return np.concatenate([a, b]).astype(np.float32)
    n = int(sr * crossfade_ms / 1000)
    if n <= 0 or n > len(a) or n > len(b):
        return np.concatenate([a, b]).astype(np.float32)
    t = np.linspace(0.0, 1.0, n, endpoint=False, dtype=np.float32)
    fade_out = np.sqrt(1.0 - t)
    fade_in = np.sqrt(t)
    cross = a[-n:] * fade_out + b[:n] * fade_in
    joined = np.concatenate([a[:-n], cross, b[n:]], dtype=np.float32)
    return joined


def micro_fade(
    signal: np.ndarray, sr: int, head_ms: int = 5, tail_ms: int = 5
) -> np.ndarray:
    """Apply short linear fades to the beginning and end of ``signal``.

    Args:
        signal: Mono signal ``[-1, 1]``.
        sr: Sample rate in Hz.
        head_ms: Fade-in duration in milliseconds.
        tail_ms: Fade-out duration in milliseconds.

    Returns:
        Faded signal in float32.
    """

    out = signal.astype(np.float32).copy()
    n_head = int(sr * head_ms / 1000)
    n_tail = int(sr * tail_ms / 1000)
    if n_head > 0:
        fade = np.linspace(0.0, 1.0, n_head, endpoint=False, dtype=np.float32)
        out[:n_head] *= fade
    if n_tail > 0:
        fade = np.linspace(1.0, 0.0, n_tail, endpoint=False, dtype=np.float32)
        out[-n_tail:] *= fade
    return out
