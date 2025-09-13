"""Placeholder adapter for a future XTTS integration."""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = ["XTTSEngine"]


class XTTSEngine:
    """Stub implementation that raises :class:`NotImplementedError`.

    The real project will provide an adapter to an XTTS engine. For testing we
    optionally allow a synthetic beep to be returned when ``allow_stub`` is set
    to ``True``.
    """

    def __init__(self, *, allow_stub: bool = False, sample_rate: int = 48000) -> None:
        self.allow_stub = allow_stub
        self.sample_rate = sample_rate

    def synthesize(
        self, text: str, voice_id: str, style: dict[str, Any] | None = None
    ) -> np.ndarray:
        """Synthesize ``text`` using XTTS or raise ``NotImplementedError``."""

        if not self.allow_stub:
            raise NotImplementedError("XTTS engine integration pending")
        t = np.linspace(0, 0.2, int(self.sample_rate * 0.2), endpoint=False)
        return (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
