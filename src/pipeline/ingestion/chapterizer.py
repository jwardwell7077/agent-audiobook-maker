from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import hashlib


@dataclass(frozen=True)
class Chapter:
    book_id: str
    chapter_id: str
    index: int
    title: str
    text: str
    text_sha256: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_title(idx: int) -> str:
    return f"Chapter {idx + 1}"


def simple_chapterize(
    book_id: str,
    text: str,
    max_chars: int = 20000,
) -> List[Chapter]:
    """
    Very simple heuristic chapterizer for placeholder purposes.
    Splits on double newlines and caps chapter size; titles are inferred.
    """
    chunks: List[str] = []
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

    chapters: List[Chapter] = []
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
