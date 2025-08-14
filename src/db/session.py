from __future__ import annotations

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError  # type: ignore
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv(
        "DB_URL",
        # Use psycopg3 driver explicitly
        "postgresql+psycopg://postgres:postgres@localhost:5432/audiobook",
    ),
)

def _init_engine():  # pragma: no cover - small bootstrap helper
    """Initialize primary engine with graceful sqlite fallback.

    In dev/test environments Postgres may not be running. Previously the
    fallback logic lived only in the pytest fixture; runtime usage (e.g.
    hitting an endpoint outside pytest) would raise OperationalError. We
    attempt a lightweight connect() to validate; on failure we transparently
    fall back to a local sqlite file so the app remains usable. In real
    production deployments Postgres should be up, so the fallback path will
    not trigger.
    """
    primary = create_engine(
        DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    try:
        with primary.connect():  # test connectivity
            pass
        return primary
    except OperationalError:  # Postgres unreachable -> fallback
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
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()
