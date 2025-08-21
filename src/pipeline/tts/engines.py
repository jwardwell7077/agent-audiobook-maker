"""Backward-compatibility shim for moved TTS engines module.

Provides import path ``pipeline.tts.engines`` while logic now lives in
``tts.engines``. Re-exports all public names.
"""

from tts.engines import *  # noqa: F401,F403

__all__: list[str] = []  # explicit export list intentionally empty
# star import sets names in importing modules; we re-export nothing new
