"""SQLite-based cache for LLM decisions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass
class LLMCache:
    """Tiny SQLite cache mapping prompt hashes to JSON results.

    Attributes:
        path: Location of the SQLite database file.
    """

    path: Path

    def __post_init__(self) -> None:
        """Create the database file and table if needed.

        Returns:
            None

        Raises:
            sqlite3.Error: If the database cannot be initialized.
        """

        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Allow access from multiple threads; protect with a lock.
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self._db.commit()

    def _key(
        self,
        *,
    roster: dict[str, list[str]],
        left: str,
        mid: str,
        right: str,
        span_type: str,
        model: str,
    ) -> str:
        """Generate a deterministic hash for the given prompt context.

        Args:
            roster: Mapping of speaker names to aliases.
            left: Text immediately preceding the span.
            mid: The span text itself.
            right: Text immediately following the span.
            span_type: Type of span being attributed.
            model: Model identifier used for the request.

        Returns:
            str: Hex digest uniquely identifying the prompt.

        Raises:
            None
        """

        h = hashlib.sha256()
        h.update(model.encode())
        h.update(json.dumps(sorted(roster.keys()), ensure_ascii=False).encode())
        h.update(span_type.encode())
        h.update(left.encode())
        h.update(mid.encode())
        h.update(right.encode())
        return h.hexdigest()

    def get(self, **kwargs: Any) -> dict[str, Any] | None:
        """Retrieve a cached result if present.

        Args:
            **kwargs: Components of the prompt used to compute the cache key.

        Returns:
            dict[str, Any] | None: Parsed JSON result or ``None`` if missing.

        Raises:
            None
        """

        k = self._key(**kwargs)
        with self._lock:
            cur = self._db.execute("SELECT value FROM cache WHERE key=?", (k,))
        row = cur.fetchone()
        if not row:
            return None
        try:
            return cast(dict[str, Any], json.loads(row[0]))
        except Exception:
            return None

    def set(self, value: dict[str, Any], **kwargs: Any) -> None:
        """Store a result in the cache.

        Args:
            value: JSON-serializable result to persist.
            **kwargs: Components of the prompt used to compute the cache key.

        Returns:
            None

        Raises:
            sqlite3.Error: If the insert fails.
        """

        k = self._key(**kwargs)
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)",
                (k, json.dumps(value, ensure_ascii=False)),
            )
            self._db.commit()

    def close(self) -> None:
        """Close the underlying database connection.

        Returns:
            None

        Raises:
            None: Errors during close are ignored.
        """

        try:
            self._db.close()
        except Exception:
            pass
