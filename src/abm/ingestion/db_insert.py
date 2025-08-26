"""Postgres inserter for Well‑Done JSONL outputs.

Design goals:
- Optional: only runs when DATABASE_URL points to Postgres; otherwise it no‑ops.
- Idempotent: unique on source_well_done; blocks keyed by (doc_id, block_index).
- Minimal deps: import psycopg only when needed to avoid hard runtime dep.

Schema (auto‑created if missing):
- welldone_documents(
        id, book, base_name, source_well_done, block_count, created_at,
        ingested_from, options, ingest_meta
    )
- welldone_blocks(doc_id, block_index, text)
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InsertResult:
    status: str  # "inserted" | "skipped" | "unavailable"
    reason: str | None = None
    doc_id: int | None = None
    inserted_blocks: int | None = None


class PgInserter:
    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.environ.get("DATABASE_URL") or ""

    def available(self) -> bool:
        # Accept postgres[ql]:// DSN; reject others (e.g., sqlite)
        return self._dsn.startswith(("postgres://", "postgresql://"))

    def insert_from_jsonl(self, jsonl_path: str | Path, meta_path: str | Path) -> InsertResult:
        if not self.available():
            return InsertResult(status="skipped", reason="DATABASE_URL not set to Postgres")
        try:
            # Lazy import to keep dependency optional
            import psycopg
            from psycopg.rows import tuple_row
        except Exception as exc:  # pragma: no cover - environment specific
            return InsertResult(status="unavailable", reason=f"psycopg not installed: {exc}")

        jl_p = Path(jsonl_path)
        mt_p = Path(meta_path)
        if not jl_p.exists() or not mt_p.exists():
            return InsertResult(status="skipped", reason="jsonl or meta path missing")

        meta = json.loads(mt_p.read_text(encoding="utf-8"))
        book = meta.get("book")
        source_well_done = meta.get("source_well_done")
        block_count = int(meta.get("block_count") or 0)
        created_at = meta.get("created_at")
        ingested_from = meta.get("ingested_from")
        options = meta.get("options")
        base_name = Path(source_well_done).stem if source_well_done else jl_p.stem

        def _iter_blocks() -> Iterable[tuple[int, str]]:
            with jl_p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    yield int(obj["index"]), str(obj["text"])

        with psycopg.connect(self._dsn, autocommit=False) as conn:
            conn.execute("SET application_name = 'abm_ingestion'")
            conn.row_factory = tuple_row
            self._ensure_schema(conn)
            with conn.cursor() as cur:
                # Upsert document row
                cur.execute(
                    """
                    INSERT INTO welldone_documents
                        (book, base_name, source_well_done, block_count, created_at,
                         ingested_from, options, ingest_meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_well_done)
                    DO UPDATE SET block_count = EXCLUDED.block_count
                    RETURNING id
                    """,
                    (
                        book,
                        base_name,
                        source_well_done,
                        block_count,
                        created_at,
                        ingested_from,
                        options if options is not None else None,
                        json.loads(mt_p.read_text(encoding="utf-8")),
                    ),
                )
                row = cur.fetchone()
                doc_id = int(row[0]) if row else None

                # Insert blocks idempotently
                inserted_blocks = 0
                ins_sql = (
                    "INSERT INTO welldone_blocks (doc_id, block_index, text) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
                )
                # Batch insert for performance
                params = [(doc_id, idx, text) for idx, text in _iter_blocks()]
                for chunk_start in range(0, len(params), 1000):
                    chunk = params[chunk_start : chunk_start + 1000]
                    cur.executemany(ins_sql, chunk)
                    inserted_blocks += len(chunk)

            conn.commit()
            return InsertResult(status="inserted", doc_id=doc_id, inserted_blocks=inserted_blocks)

    def _ensure_schema(self, conn: Any) -> None:
        # Create tables if they do not exist. Keep simple and portable.
        ddl_docs = """
        CREATE TABLE IF NOT EXISTS welldone_documents (
            id BIGSERIAL PRIMARY KEY,
            book TEXT,
            base_name TEXT NOT NULL,
            source_well_done TEXT NOT NULL UNIQUE,
            block_count INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            ingested_from TEXT,
            options JSONB,
            ingest_meta JSONB
        );
        """
        ddl_blocks = """
        CREATE TABLE IF NOT EXISTS welldone_blocks (
            doc_id BIGINT NOT NULL REFERENCES welldone_documents(id) ON DELETE CASCADE,
            block_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (doc_id, block_index)
        );
        CREATE INDEX IF NOT EXISTS idx_welldone_blocks_doc ON welldone_blocks(doc_id);
        """
        conn.execute(ddl_docs)
        conn.execute(ddl_blocks)
