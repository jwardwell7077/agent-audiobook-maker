from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from abm.ingestion.db_insert import PgInserter


def test_available_checks_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    ins = PgInserter(dsn="sqlite:///dev.db")
    assert ins.available() is False
    ins = PgInserter(dsn="postgresql://localhost/db")
    assert ins.available() is True


def test_insert_skips_when_not_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jl = tmp_path / "a.jsonl"
    mt = tmp_path / "a_meta.json"
    ins = PgInserter(dsn="sqlite:///dev.db")
    res = ins.insert_from_jsonl(jl, mt)
    assert res.status in {"skipped", "unavailable"}


def test_insert_unavailable_when_psycopg_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    jl = tmp_path / "a.jsonl"
    jl.write_text("{}\n", encoding="utf-8")
    mt = tmp_path / "a_meta.json"
    mt.write_text(json.dumps({"source_well_done": str(jl), "block_count": 1}), encoding="utf-8")

    # Force available() to be True
    ins = PgInserter(dsn="postgresql://localhost/db")

    # Simulate ImportError in psycopg import path
    def _import_fail(*_a: Any, **_kw: Any) -> Any:
        raise ImportError("psycopg not installed")

    monkeypatch.setitem(os.environ, "DATABASE_URL", "postgresql://localhost/db")
    # Monkeypatch the module import by injecting a dummy name in sys.modules
    # Here, we trigger the exception path by replacing __import__ of psycopg via monkeypatch context.
    with monkeypatch.context() as m:
        m.setenv("DATABASE_URL", "postgresql://localhost/db")
        # The code uses a normal import; easiest is to shadow module name in sys.modules with a raising proxy
        import sys

        class _Raiser:
            def __getattr__(self, _name: str) -> Any:
                raise ImportError("psycopg not installed")

        sys.modules.pop("psycopg", None)
        sys.modules["psycopg"] = _Raiser()  # type: ignore[assignment]
        res = ins.insert_from_jsonl(jl, mt)
        assert res.status == "unavailable"
