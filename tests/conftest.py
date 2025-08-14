import sys
from pathlib import Path
import pytest

from sqlalchemy.exc import OperationalError  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# Ensure a clean database (sqlite by default) before each test for isolation.
@pytest.fixture(autouse=True)
def _clean_db():  # pragma: no cover - test infra
    """Ensure clean DB per test.

    Attempts to use configured (likely Postgres) engine; if unavailable
    (e.g. local dev without docker running), transparently falls back to
    a local sqlite file so tests can still run. This avoids hard test
    dependency on external service while keeping production path intact.
    """
    try:
        from db import session as session_mod  # type: ignore
        from db.models import Base  # type: ignore
    except Exception:  # noqa: BLE001
        yield
        return
    engine = session_mod.engine
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    except OperationalError:  # Postgres not up -> fallback
        from sqlalchemy import create_engine  # type: ignore

        fallback_url = "sqlite:///./test_fallback.db"
        engine = create_engine(
            fallback_url, future=True, pool_pre_ping=True
        )
        # Rebind existing sessionmaker
        session_mod.engine = engine  # type: ignore
        session_mod.SessionLocal.configure(bind=engine)  # type: ignore
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    yield
