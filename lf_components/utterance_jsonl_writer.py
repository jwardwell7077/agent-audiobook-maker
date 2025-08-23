from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Iterable


def _default_stem() -> str:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"segments_{ts}"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_jsonl(
    book: str,
    utterances: Iterable[dict[str, Any]],
    base_dir: Path | None = None,
    stem: str | None = None,
) -> Path:
    root = base_dir or Path.cwd()
    out_dir = root / "data" / "annotations" / book
    _ensure_dir(out_dir)
    name = (stem or _default_stem()) + ".jsonl"
    out_path = out_dir / name
    header = {
        "version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "book": book,
        "type": "utterances",
    }
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"header": header}, ensure_ascii=False) + "\n")
        for u in utterances:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    return out_path


def run(
    payload: dict[str, Any],
    base_dir: str | None = None,
    stem: str | None = None,
) -> dict[str, Any]:
    book = payload.get("book", "")
    utterances = payload.get("utterances", [])
    out_path = write_jsonl(
        book,
        utterances,
        Path(base_dir) if base_dir else None,
        stem,
    )
    return {"book": book, "path": str(out_path), "count": len(utterances)}
