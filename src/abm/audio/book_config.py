"""Book metadata schema and loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

__all__ = ["BookMeta", "load_book_meta"]


@dataclass(slots=True)
class BookMeta:
    """Metadata describing an audiobook."""

    title: str
    author: str
    series: str | None = None
    language: str | None = None
    year: int | None = None
    cover: Path | None = None
    publisher: str | None = None


def load_book_meta(path: str | Path) -> BookMeta:
    """Load :class:`BookMeta` from a YAML file.

    Args:
        path: Path to a ``book.yaml`` file.

    Returns:
        Parsed :class:`BookMeta` instance.

    Raises:
        FileNotFoundError: If the cover image does not exist.
        ValueError: If required fields are missing.
    """

    src = Path(path)
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    required = ["title", "author", "cover"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    cover = Path(data["cover"]).expanduser()
    if not cover.exists():
        raise FileNotFoundError(f"cover image not found: {cover}")
    return BookMeta(
        title=str(data["title"]),
        author=str(data["author"]),
        series=data.get("series"),
        language=data.get("language"),
        year=int(data["year"]) if "year" in data else None,
        cover=cover,
        publisher=data.get("publisher"),
    )
