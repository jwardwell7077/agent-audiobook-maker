from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    body_text: str


def load_chapters_json(
    book: str, base_dir: Path | None = None
) -> List[Chapter]:
    """Load chapters from data/clean/<book>/chapters.json.

    Args:
        book: short book key, e.g. "mvs".
        base_dir: project root (defaults to repo root inferred from cwd).

    Returns:
        List of Chapter objects.
    """
    root = base_dir or Path.cwd()
    path = root / "data" / "clean" / book / "chapters.json"
    if not path.exists():  # prefer deterministic behavior
        raise FileNotFoundError(f"Missing chapters file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    chapters = []
    for item in data.get("chapters", []):
        body = item.get("body_text") or ""
        chapters.append(
            Chapter(
                index=int(item.get("index", 0)),
                title=str(item.get("title", "")),
                body_text=body,
            )
        )
    return chapters


def run(
    book: str, base_dir: Optional[str] = None, limit: Optional[int] = None
) -> Dict[str, Any]:
    """LangFlow-compatible entry: returns a dict with book and chapters.

    limit: optionally limit number of chapters for quick experiments.
    """
    chapters = load_chapters_json(book, Path(base_dir) if base_dir else None)
    if limit is not None:
        chapters = chapters[: int(limit)]
    payload = {
        "book": book,
        "chapters": [
            {
                "index": c.index,
                "title": c.title,
                "body_text": c.body_text,
            }
            for c in chapters
        ],
    }
    return payload
