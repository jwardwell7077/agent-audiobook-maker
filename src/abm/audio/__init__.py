"""Audio synthesis interfaces and engine registry.

This package provides base classes for TTS adapters, concrete engine
implementations, and a registry for engine factories.
"""


def register_builtins() -> None:
    """Register built-in adapters with :class:`EngineRegistry`.

    Importing adapters triggers registration side effects. Calling this
    function multiple times is safe.
    """
    from abm.audio.engine_registry import EngineRegistry
    from abm.audio.piper_adapter import PiperAdapter
    from abm.audio.xtts_adapter import XTTSAdapter

    for name, adapter in {
        "piper": PiperAdapter,
        "xtts": XTTSAdapter,
    }.items():
        try:
            EngineRegistry.register(name, lambda _adapter=adapter, **kw: _adapter(**kw))
        except ValueError:
            pass


__all__ = ["tts_base", "engine_registry", "register_builtins"]
