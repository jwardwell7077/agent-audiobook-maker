"""Simple registry/factory for TTS engine adapters."""

from __future__ import annotations

import threading
from collections.abc import Callable

from abm.audio.tts_base import TTSAdapter

# Factory signature: kwargs allow engine-specific options
Factory = Callable[..., TTSAdapter]


class EngineRegistry:
    """Global registry for TTS engine factories.

    This avoids hard-coding adapter imports throughout the codebase.
    """

    _lock = threading.RLock()
    _factories: dict[str, Factory] = {}

    @classmethod
    def register(cls, name: str, factory: Factory) -> None:
        """Register a factory under a unique engine name.

        Args:
            name: Engine key (e.g., "piper", "xtts").
            factory: Callable that returns a ready-to-use :class:`TTSAdapter`.

        Raises:
            ValueError: If a factory is already registered for ``name``.
        """
        key = name.strip().lower()
        with cls._lock:
            if key in cls._factories:
                raise ValueError(f"Factory already registered: {key}")
            cls._factories[key] = factory

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove a factory by name (no-op if missing)."""
        key = name.strip().lower()
        with cls._lock:
            cls._factories.pop(key, None)

    @classmethod
    def create(cls, name: str, **kwargs) -> TTSAdapter:
        """Instantiate an adapter by engine name.

        Args:
            name: Engine key to instantiate.
            **kwargs: Engine-specific keyword arguments forwarded to the factory.

        Returns:
            A new :class:`TTSAdapter` instance.

        Raises:
            KeyError: If ``name`` is not registered.
        """
        key = name.strip().lower()
        with cls._lock:
            factory = cls._factories.get(key)
        if factory is None:
            raise KeyError(f"Unknown engine: {name}")
        return factory(**kwargs)

    @classmethod
    def list_engines(cls) -> list[str]:
        """Return a sorted list of registered engine names."""
        with cls._lock:
            return sorted(cls._factories.keys())
