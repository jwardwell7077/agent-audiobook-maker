"""Simple registry for TTS adapters."""

from __future__ import annotations

from collections.abc import Callable

from abm.audio.tts_base import TTSAdapter


class EngineRegistry:
    """Registry mapping engine identifiers to adapter factories."""

    _builders: dict[str, Callable[..., TTSAdapter]] = {}

    @classmethod
    def register(cls, engine_id: str, builder: Callable[..., TTSAdapter]) -> None:
        """Register a builder for an engine.

        Args:
            engine_id: Unique engine identifier.
            builder: Callable returning a :class:`TTSAdapter`.
        """

        cls._builders[engine_id] = builder

    @classmethod
    def create(cls, engine_id: str, **kwargs) -> TTSAdapter:
        """Create an adapter for the given engine.

        Args:
            engine_id: Engine identifier registered via :meth:`register`.
            **kwargs: Forwarded to the builder.

        Returns:
            Instance of :class:`TTSAdapter`.

        Raises:
            KeyError: If engine_id is unknown.
        """

        try:
            builder = cls._builders[engine_id]
        except KeyError as exc:  # pragma: no cover - trivial
            raise KeyError(f"Unknown TTS engine '{engine_id}'") from exc
        return builder(**kwargs)
