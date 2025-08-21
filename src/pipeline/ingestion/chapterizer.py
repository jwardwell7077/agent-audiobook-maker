"""Basic heuristic chapterization utilities.

Provides a simple paragraph-based splitter used as a fallback or
baseline when no structured TOC / heading strategy is available.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chapter:
    book_id: str
    chapter_id: str
    index: int
    title: str
    text: str
    text_sha256: str


def sha256_text(text: str) -> str:
    """Return hex SHA-256 digest of ``text``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_title(idx: int) -> str:
    """Return default chapter title (1-based)."""
    return f"Chapter {idx + 1}"


def simple_chapterize(
    book_id: str,
    text: str,
    max_chars: int = 20000,
) -> list[Chapter]:
    """Split ``text`` into approximate chapters.

    Heuristic: group paragraphs (double newline separated) into chunks
    not exceeding ``max_chars``; assign default titles.
    """
    chunks: list[str] = []
    buf: list[str] = []
    current = 0
    for para in text.split("\n\n"):
        if current + len(para) + 2 > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf = []
            current = 0
        buf.append(para)
        current += len(para) + 2
    if buf:
        chunks.append("\n\n".join(buf))

    chapters: list[Chapter] = []
    for i, chunk in enumerate(chunks):
        title = default_title(i)
        chapters.append(
            Chapter(
                book_id=book_id,
                chapter_id=f"{i:05d}",
                index=i,
                title=title,
                text=chunk,
                text_sha256=sha256_text(chunk),
            )
        )
    return chapters


def write_chapter_json(chapter: Chapter, out_dir: Path) -> Path:
    """Write chapter to ``out_dir`` returning the file path."""
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{chapter.chapter_id}.json"
    payload = {
        "book_id": chapter.book_id,
        "chapter_id": chapter.chapter_id,
        "index": chapter.index,
        "title": chapter.title,
        "text": chapter.text,
        "text_sha256": chapter.text_sha256,
    }
    p.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return p
