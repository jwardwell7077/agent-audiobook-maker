from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from abm.ingestion.db_insert import PgInserter


class _MiniConn:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.row_factory: Any = None

    def execute(self, sql: str, *_: Any) -> None:
        self.executed.append(sql)

    def cursor(self) -> Any:  # noqa: D401 - stub
        raise AssertionError("should not be called for missing files")

    def __enter__(self) -> _MiniConn:  # noqa: D401 - stub
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # noqa: D401 - stub
        return None


class _MiniPsycopg:
    def __init__(self) -> None:
        self._conn = _MiniConn()

    def connect(self, dsn: str, autocommit: bool = False) -> _MiniConn:  # noqa: D401 - stub
        return self._conn


class _Rows:
    tuple_row = object()


def test_skips_when_files_missing_but_psycopg_import_succeeds(tmp_path: Path) -> None:
    # Inject minimal psycopg so import works
    sys.modules.pop("psycopg", None)
    sys.modules.pop("psycopg.rows", None)
    sys.modules["psycopg"] = _MiniPsycopg()  # type: ignore[assignment]
    sys.modules["psycopg.rows"] = _Rows()  # type: ignore[assignment]

    ins = PgInserter(dsn="postgresql://localhost/db")
    res = ins.insert_from_jsonl(tmp_path / "missing.jsonl", tmp_path / "missing_meta.json")
    assert res.status == "skipped" and "missing" in (res.reason or "")


class _CapCursor:
    def __init__(self) -> None:
        self.params: list[tuple[Any, ...] | None] = []

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:  # noqa: D401 - stub
        self.params.append(params)

    def fetchone(self) -> tuple[int]:  # noqa: D401 - stub
        return (1,)

    def executemany(self, sql: str, seq_of_params: list[tuple[Any, ...]]) -> None:  # noqa: D401 - stub
        pass

    def __enter__(self) -> _CapCursor:  # noqa: D401 - stub
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # noqa: D401 - stub
        return None


class _CapConn(_MiniConn):
    def __init__(self) -> None:
        super().__init__()
        self._cur = _CapCursor()
        self.committed = False

    def cursor(self) -> _CapCursor:  # noqa: D401 - stub
        return self._cur

    def commit(self) -> None:  # noqa: D401 - stub
        self.committed = True


class _CapPsycopg(_MiniPsycopg):
    def __init__(self) -> None:
        self._conn = _CapConn()


def test_base_name_from_jsonl_stem_and_options_none(tmp_path: Path) -> None:
    # Arrange: create jsonl and meta without source_well_done or options
    jl = tmp_path / "c.jsonl"
    jl.write_text('{"index":0,"text":"A"}\n', encoding="utf-8")
    meta = tmp_path / "c_meta.json"
    meta.write_text(json.dumps({"block_count": 1, "created_at": "x"}), encoding="utf-8")

    # Inject captor psycopg
    sys.modules["psycopg"] = _CapPsycopg()  # type: ignore[assignment]
    sys.modules["psycopg.rows"] = _Rows()  # type: ignore[assignment]

    ins = PgInserter(dsn="postgresql://localhost/db")
    res = ins.insert_from_jsonl(jl, meta)
    assert res.status == "inserted"
    # Validate params used for base_name and options None: it's the first execute after ensure_schema
    cap_conn: _CapConn = sys.modules["psycopg"]._conn  # type: ignore[attr-defined]
    params = cap_conn._cur.params[0]
    assert params is not None
    # order: (book, base_name, source_well_done, block_count, created_at, ingested_from, options, ingest_meta)
    assert params[1] == "c"  # base_name from jl.stem
    assert params[2] is None  # source_well_done None
    assert params[6] is None  # options None path covered
