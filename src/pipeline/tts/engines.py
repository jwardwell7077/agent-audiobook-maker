"""Deprecated: use src.tts.engines instead.

This module is kept temporarily for backward compatibility and will be
removed after migration completes.
"""
from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "src.pipeline.tts.engines is deprecated; import src.tts.engines instead",
    DeprecationWarning,
    stacklevel=2,
)

from src.tts.engines import *  # noqa: F401,F403
