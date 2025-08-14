from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from functools import wraps
from typing import Callable, Any
import inspect

TRACE_LEVEL = 5
if not hasattr(logging, "TRACE"):
    logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(
    self: logging.Logger, msg: str, *args, **kwargs
) -> None:  # pragma: no cover - simple passthrough
    if self.isEnabledFor(TRACE_LEVEL):  # pragma: no branch
        self._log(TRACE_LEVEL, msg, args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]

DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(module)s | %(funcName)s | "
    "%(message)s"
)


class MinLevelFilter(logging.Filter):
    def __init__(self, min_level: int) -> None:
        super().__init__()
        self._min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        return record.levelno >= self._min_level


def setup_logging(force: bool = False) -> None:
    if getattr(setup_logging, "_configured", False) and not force:
        return
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if force:  # pragma: no cover
        for h in list(root.handlers):
            root.removeHandler(h)
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    if level_name == "TRACE":
        level = TRACE_LEVEL
    else:
        level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)
    fmt = logging.Formatter(DEFAULT_FORMAT)
    info_handler = TimedRotatingFileHandler(
        log_dir / "app.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    info_handler.setFormatter(fmt)
    info_handler.setLevel(logging.INFO)
    debug_handler = TimedRotatingFileHandler(
        log_dir / "app-debug.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    debug_handler.setFormatter(fmt)
    debug_handler.setLevel(TRACE_LEVEL)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(level)
    root.addHandler(info_handler)
    root.addHandler(debug_handler)
    root.addHandler(console)
    setup_logging._configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def log_call(
    level: int = logging.DEBUG,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        logger = get_logger(fn.__module__)
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def _wrapped(
                *args, **kwargs
            ):  # pragma: no cover - instrumentation
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
                    if logger.isEnabledFor(level):
                        logger.log(
                            level,
                            "EXIT %s -> %s",
                            fn.__qualname__,
                            _shorten(result),
                        )
                    return result
                except Exception as e:  # noqa: BLE001
                    logger.exception("ERROR in %s: %s", fn.__qualname__, e)
                    raise
        else:

            @wraps(fn)
            def _wrapped(
                *args, **kwargs
            ):  # pragma: no cover - instrumentation
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
                    if logger.isEnabledFor(level):
                        logger.log(
                            level,
                            "EXIT %s -> %s",
                            fn.__qualname__,
                            _shorten(result),
                        )
                    return result
                except Exception as e:  # noqa: BLE001
                    logger.exception("ERROR in %s: %s", fn.__qualname__, e)
                    raise
        return _wrapped

    return _decorator


def _shorten(obj: Any, limit: int = 120) -> Any:
    try:  # pragma: no cover
        s = repr(obj)
        if len(s) > limit:
            return s[: limit - 3] + "..."
        return s
    except Exception:  # noqa: BLE001
        return type(obj).__name__
