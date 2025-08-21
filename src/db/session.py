"""Session factory utilities for database access.

The project currently uses a single engine + scoped session pattern; this
module centralises creation so tests can swap configuration if needed.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv(
        "DB_URL",
        # Use psycopg3 driver explicitly
        "postgresql+psycopg://postgres:postgres@localhost:5432/audiobook",
    ),
)


logger = logging.getLogger(__name__)


def _init_engine() -> Engine:  # pragma: no cover - small bootstrap helper
    """Initialize primary engine with graceful sqlite fallback.

    In dev/test environments Postgres may not be running. Previously the
    fallback logic lived only in the pytest fixture; runtime usage (e.g.
    hitting an endpoint outside pytest) would raise OperationalError. We
    attempt a lightweight connect() to validate; on failure we transparently
    fall back to a local sqlite file so the app remains usable. In real
    production deployments Postgres should be up, so the fallback path will
    not trigger.
    """
    try:
        primary = create_engine(
            DATABASE_URL,
            future=True,
            pool_pre_ping=True,
        )
        try:
            with primary.connect():  # test connectivity
                pass
            return primary
        except OperationalError as exc:
            # Postgres unreachable -> fallback
            logger.warning("Primary DB unavailable; falling back to sqlite. err=%s", exc)
    except Exception as exc:  # noqa: BLE001
        # Driver import error or other engine creation failure -> fallback
        logger.warning("DB engine init failed; using sqlite fallback. err=%s", exc)
    fallback_url = "sqlite:///./test_fallback.db"
    fallback = create_engine(
        fallback_url,
        future=True,
        pool_pre_ping=True,
    )
    return fallback


engine = _init_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager yielding a SQLAlchemy session and ensuring close."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()
