from abm.audio import register_builtins
from abm.audio.engine_registry import EngineRegistry


def test_register_builtins_idempotent():
    EngineRegistry.unregister("piper")
    EngineRegistry.unregister("xtts")
    register_builtins()
    engines_once = EngineRegistry.list_engines()
    register_builtins()
    engines_twice = EngineRegistry.list_engines()
    assert engines_once == engines_twice
    assert "piper" in engines_twice and "xtts" in engines_twice
