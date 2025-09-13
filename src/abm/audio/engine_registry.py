"""Registry for TTS engines."""

from __future__ import annotations

from collections.abc import Callable

from abm.audio.tts_base import TTSAdapter


class EngineRegistry:
    """Factory registry for TTS adapters."""

    _registry: dict[str, Callable[..., TTSAdapter]] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[..., TTSAdapter]) -> None:
        """Register a factory for an engine.

        Args:
            name: Engine identifier.
            factory: Callable that returns an adapter instance.
        """
        cls._registry[name] = factory

    @classmethod
    def create(cls, name: str, **kwargs) -> TTSAdapter:
        """Create an adapter by name.

        Args:
            name: Engine identifier.
            **kwargs: Passed to the registered factory.

        Returns:
            A TTS adapter instance.

        Raises:
            KeyError: If the engine is not registered.
        """
        if name not in cls._registry:
            raise KeyError(f"Unknown TTS engine: {name}")
        return cls._registry[name](**kwargs)
