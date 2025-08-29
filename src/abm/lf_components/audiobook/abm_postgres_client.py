"""ABM Postgres Client for LangFlow.

Provides simple query/execute operations against a PostgreSQL database.
Uses psycopg (v3) with dict_row for friendly records.
"""

from __future__ import annotations

import os
from typing import Any  # noqa: F401

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, IntInput, MessageTextInput, Output
from langflow.schema import Data


class ABMPostgresClient(Component):
    display_name = "ABM Postgres Client"
    description = "Run SQL queries against PostgreSQL (query/execute)"
    icon = "database"
    name = "ABMPostgresClient"

    inputs = [
        # Connection
        MessageTextInput(
            name="dsn",
            display_name="DSN (optional)",
            info="Postgres connection string; if empty, use host/port/db/user/password",
            required=False,
            value=os.getenv("PG_DSN", ""),
        ),
        MessageTextInput(name="host", display_name="Host", value=os.getenv("PGHOST", "localhost")),
        IntInput(name="port", display_name="Port", value=int(os.getenv("PGPORT", "5432"))),
        MessageTextInput(name="dbname", display_name="Database", value=os.getenv("PGDATABASE", "postgres")),
        MessageTextInput(name="user", display_name="User", value=os.getenv("PGUSER", "postgres")),
        MessageTextInput(
            name="password",
            display_name="Password",
            value=os.getenv("PGPASSWORD", ""),
        ),
        BoolInput(
            name="autocommit",
            display_name="Autocommit",
            value=True,
            info="Commit automatically for execute operations",
        ),
        # Operation inputs
        MessageTextInput(
            name="sql",
            display_name="SQL",
            info="Query or statement to execute",
            required=False,
        ),
        DataInput(
            name="params",
            display_name="Parameters",
            info="Query parameters (list/tuple for positional, dict for named)",
            required=False,
        ),
        IntInput(
            name="fetch_limit",
            display_name="Fetch Limit",
            value=1000,
            info="Max rows to fetch for query()",
        ),
    ]

    outputs = [
        Output(display_name="Query Result", name="query_result", method="query"),
        Output(display_name="Execute Result", name="execute_result", method="execute"),
    ]

    def _connect(self):  # type: ignore[no-untyped-def]
        try:
            import psycopg
            from psycopg.rows import dict_row
        except Exception as e:  # pragma: no cover - import guard
            raise RuntimeError("psycopg not installed. Install with 'pip install psycopg[binary]'.") from e

        if getattr(self, "dsn", None):
            conn = psycopg.connect(self.dsn, autocommit=self.autocommit, row_factory=dict_row)
        else:
            conn = psycopg.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                autocommit=self.autocommit,
                row_factory=dict_row,
            )
        return conn

    def query(self) -> Data:
        """Run a SELECT-like query and return rows as list[dict]."""
        sql = (getattr(self, "sql", None) or "").strip()
        if not sql:
            return Data(data={"error": "No SQL provided"})

        try:
            conn = self._connect()
            with conn:  # ensures proper closing
                with conn.cursor() as cur:
                    cur.execute(sql, getattr(self, "params", None))
                    rows = cur.fetchmany(size=self.fetch_limit)
            self.status = f"Fetched {len(rows)} rows"
            return Data(data={"rows": rows, "rowcount": len(rows)})
        except Exception as e:  # noqa: BLE001
            self.status = f"Error: {e}"
            return Data(data={"error": str(e)})

    def execute(self) -> Data:
        """Run a non-SELECT statement (INSERT/UPDATE/DELETE/DDL)."""
        sql = (getattr(self, "sql", None) or "").strip()
        if not sql:
            return Data(data={"error": "No SQL provided"})

        try:
            conn = self._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql, getattr(self, "params", None))
                    rowcount = cur.rowcount
            self.status = f"Executed ({rowcount} affected)"
            return Data(data={"rowcount": rowcount})
        except Exception as e:  # noqa: BLE001
            self.status = f"Error: {e}"
            return Data(data={"error": str(e)})
