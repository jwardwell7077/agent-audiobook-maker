"""Cache utilities for synthesized segments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

__all__ = ["make_cache_key", "cache_path"]


def make_cache_key(payload: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 key for ``payload``.

    Args:
        payload: Serializable dictionary describing a TTS request. The
            dictionary is JSON-encoded with stable ordering.

    Returns:
        Hexadecimal digest representing the payload.
    """

    serial = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


def cache_path(root: Path, engine: str, voice: str, key: str) -> Path:
    """Return the expected cache path for ``engine``/``voice``/``key``.

    Args:
        root: Root directory of the cache.
        engine: Engine identifier.
        voice: Voice identifier within the engine.
        key: Cache key obtained from :func:`make_cache_key`.

    Returns:
        Path to the ``.wav`` file for the cached segment.
    """

    return root / engine / voice / f"{key}.wav"
