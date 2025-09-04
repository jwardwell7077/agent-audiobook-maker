from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from abm.ingestion.db_insert import PgInserter


class _FakeCursor:
    def __init__(self, ret_id: int) -> None:
        self.statements: list[tuple[str, tuple[Any, ...] | None]] = []
        self._ret_id = ret_id
        self._executemany_batches: list[list[tuple[Any, ...]]] = []

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:  # noqa: D401 - stub
        self.statements.append((sql, params))

    def fetchone(self) -> tuple[int]:  # noqa: D401 - stub
        return (self._ret_id,)

    def executemany(self, sql: str, seq_of_params: list[tuple[Any, ...]]) -> None:  # noqa: D401 - stub
        # Record the batch and pretend success
        self.statements.append((sql, None))
        self._executemany_batches.append(list(seq_of_params))

    # Context manager support
    def __enter__(self) -> _FakeCursor:  # noqa: D401 - stub
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401 - stub
        return None


class _FakeConn:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.row_factory: Any = None
        self._cursor = _FakeCursor(ret_id=42)
        self.committed = False

    # psycopg API shims
    def execute(self, sql: str, *_: Any) -> None:  # noqa: D401 - stub
        self.executed.append(sql)

    def cursor(self) -> _FakeCursor:  # noqa: D401 - stub
        return self._cursor

    def commit(self) -> None:  # noqa: D401 - stub
        self.committed = True

    # Context manager support
    def __enter__(self) -> _FakeConn:  # noqa: D401 - stub
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401 - stub
        return None


class _FakePsycopgModule:
    def __init__(self) -> None:
        self._conn = _FakeConn()

    def connect(self, dsn: str, autocommit: bool = False) -> _FakeConn:  # noqa: D401 - stub
        return self._conn


class _FakeRowsModule:
    tuple_row = object()


def test_inserted_path_with_mocked_psycopg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Prepare JSONL with 3 blocks and minimal meta
    jl = tmp_path / "b.jsonl"
    jl.write_text(
        (
            """
{"index": 0, "text": "A"}

{"index": 1, "text": "B"}
{"index": 2, "text": "C"}
"""
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    meta = tmp_path / "b_meta.json"
    meta.write_text(
        json.dumps(
            {
                "book": "bk",
                "source_well_done": str(tmp_path / "b_well_done.txt"),
                "block_count": 3,
                "created_at": "2020-01-01T00:00:00Z",
                "ingested_from": None,
                "options": {"opt": True},
            }
        ),
        encoding="utf-8",
    )

    # Inject fake psycopg and psycopg.rows into sys.modules
    sys.modules.pop("psycopg", None)
    sys.modules.pop("psycopg.rows", None)
    fake_psycopg = _FakePsycopgModule()
    sys.modules["psycopg"] = fake_psycopg  # type: ignore[assignment]
    sys.modules["psycopg.rows"] = _FakeRowsModule()  # type: ignore[assignment]

    ins = PgInserter(dsn="postgresql://localhost/db")
    res = ins.insert_from_jsonl(jl, meta)

    assert res.status == "inserted"
    assert res.inserted_blocks == 3
    # Ensure schema DDLs executed and commit called
    assert any("CREATE TABLE IF NOT EXISTS welldone_documents" in s for s in fake_psycopg._conn.executed)
    assert fake_psycopg._conn.committed is True
