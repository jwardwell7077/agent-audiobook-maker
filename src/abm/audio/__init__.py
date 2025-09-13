"""Audio synthesis interfaces and engine registry.

This package provides base classes for TTS adapters, concrete engine
implementations, and a registry for engine factories.

Importing this package auto-registers the built-in adapters so they can be
instantiated via :class:`abm.audio.engine_registry.EngineRegistry` without
additional imports.
"""

# Import adapters for side effects (EngineRegistry registration).
from abm.audio import piper_adapter, xtts_adapter  # noqa: F401

__all__ = [
    "tts_base",
    "engine_registry",
    "piper_adapter",
    "xtts_adapter",
]
