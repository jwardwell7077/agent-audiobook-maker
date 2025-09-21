from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List

import orjson


def load_chapters(paths: Iterable[str]) -> List[dict[str, str]]:
    """Load chapter JSON files and normalize into a common structure."""
    chapters: List[dict[str, str]] = []
    counter = 0

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"Chapter file not found: {path_str}")

        raw = orjson.loads(path.read_bytes())
        if isinstance(raw, dict):
            records = raw.get("chapters", [])
        elif isinstance(raw, list):
            records = raw
        else:
            raise ValueError(f"Unsupported chapter format in {path_str!s}")

        if not isinstance(records, list):
            raise ValueError(f"Expected a list of chapters in {path_str!s}")

        for record in records:
            if not isinstance(record, dict):
                continue

            counter += 1
            text = str(record.get("text", ""))
            title = str(record.get("title") or record.get("name") or f"Chapter {counter}")
            chapter_id = record.get("id") or record.get("chapter_id") or f"ch_{counter:04d}"

            chapters.append({
                "id": str(chapter_id),
                "title": title,
                "text": text,
            })

    return chapters


def save_json(path: str | Path, obj: Any) -> None:
    """Serialize ``obj`` to ``path`` using orjson with indentation."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = orjson.dumps(obj, option=orjson.OPT_INDENT_2 | orjson.OPT_SERIALIZE_NUMPY)
    target.write_bytes(data)
