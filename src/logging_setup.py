"""Unified logging configuration used by both API and scripts.

Provides helpers:
* ``setup_logging`` – idempotent configuration with stderr INFO and optional
    debug stream.
* ``get_logger`` – convenience that ensures configuration first.
* ``log_call`` – lightweight decorator for entry/exit tracing.
"""

from __future__ import annotations

import inspect
import logging
import os
from collections.abc import Callable
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

# ----- Custom TRACE level -------------------------------------------------
TRACE_LEVEL = 5
if not hasattr(logging, "TRACE"):
    logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(
    self: logging.Logger,
    msg: str,
    *args: object,
    **kwargs: object,
) -> None:  # pragma: no cover - simple passthrough
    if self.isEnabledFor(TRACE_LEVEL):  # pragma: no branch
        self._log(TRACE_LEVEL, msg, args, **kwargs)  # type: ignore[arg-type]


logging.Logger.trace = _trace  # type: ignore[attr-defined]

# ----- Formatter -----------------------------------------------------------
DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(module)s | %(funcName)s | %(message)s"


class MinLevelFilter(logging.Filter):
    """Filter allowing only records >= a minimum level."""

    def __init__(self, min_level: int) -> None:
        """Store the minimum level; invoked by logging when handler added."""
        super().__init__()
        self._min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        """Decide if the record should be emitted (meets threshold)."""
        return record.levelno >= self._min_level


def setup_logging(force: bool = False) -> None:
    """Configure root logging for the application.

    Creates two daily rotating file handlers (info & debug) keeping 7 backups
    and a console stream handler for stdout (so uvicorn displays output).
    Idempotent: call once at import time.
    """
    if getattr(setup_logging, "_configured", False) and not force:
        return

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    # Clear existing handlers only if forcing
    if force:  # pragma: no cover
        for h in list(root.handlers):
            root.removeHandler(h)

    # Determine global level from env; default INFO
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    if level_name == "TRACE":
        level = TRACE_LEVEL
    else:
        level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    fmt = logging.Formatter(DEFAULT_FORMAT)

    # Info+ handler
    info_handler = TimedRotatingFileHandler(
        log_dir / "app.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    info_handler.setFormatter(fmt)
    info_handler.setLevel(logging.INFO)

    # Debug/Trace handler
    debug_handler = TimedRotatingFileHandler(
        log_dir / "app-debug.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    debug_handler.setFormatter(fmt)
    debug_handler.setLevel(TRACE_LEVEL)

    # Console (stdout)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(level)

    root.addHandler(info_handler)
    root.addHandler(debug_handler)
    root.addHandler(console)

    setup_logging._configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Return a logger ensuring configuration is applied first."""
    setup_logging()
    return logging.getLogger(name)


P = ParamSpec("P")
R = TypeVar("R")


def log_call(
    level: int = logging.DEBUG,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Return decorator logging entry/exit of target function.

    Example::

        @log_call()
        def my_func(a, b): ...
    """

    def _decorator(fn: Callable[P, Any]) -> Callable[P, Any]:
        logger = get_logger(fn.__module__)
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:  # pragma: no cover
                if logger.isEnabledFor(level):
                    logger.log(
                        level,
                        "ENTER %s args=%s kwargs=%s",
                        fn.__qualname__,
                        _shorten(args),
                        _shorten(kwargs),
                    )
                try:
                    result = await fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    logger.exception("ERROR in %s: %s", fn.__qualname__, e)
                    raise
                if logger.isEnabledFor(level):
                    logger.log(
                        level,
                        "EXIT %s -> %s",
                        fn.__qualname__,
                        _shorten(result),
                    )
                return result

            return async_wrapper
        else:

            @wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:  # pragma: no cover
                if logger.isEnabledFor(level):
                    logger.log(
                        level,
                        "ENTER %s args=%s kwargs=%s",
                        fn.__qualname__,
                        _shorten(args),
                        _shorten(kwargs),
                    )
                try:
                    result = fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    logger.exception("ERROR in %s: %s", fn.__qualname__, e)
                    raise
                if logger.isEnabledFor(level):
                    logger.log(
                        level,
                        "EXIT %s -> %s",
                        fn.__qualname__,
                        _shorten(result),
                    )
                return result

            return sync_wrapper

    return _decorator


def _shorten(obj: object, limit: int = 120) -> str:
    """Return a truncated repr for logging (never raises)."""
    try:  # pragma: no cover - defensive
        s = repr(obj)
        if len(s) > limit:
            return s[: limit - 3] + "..."
        return s
    except Exception:  # noqa: BLE001
        return type(obj).__name__
