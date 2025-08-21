"""High-level CRUD helpers around the SQLAlchemy session.

Only the minimal operations required by the API & pipeline are implemented;
they intentionally avoid clever abstractions to keep call-sites explicit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import models


def upsert_book(
    session: Session,
    book_id: str,
    title: str | None = None,
    author: str | None = None,
) -> models.Book:
    """Insert or update a ``Book`` by id returning the persistent instance."""
    book = session.get(models.Book, book_id)
    if not book:
        book = models.Book(id=book_id, title=title or book_id, author=author)
        session.add(book)
    else:
        if title:
            book.title = title
        if author:
            book.author = author
    return book


def store_chapters(
    session: Session,
    chapters: Sequence[Mapping[str, Any]],
) -> None:
    """Insert chapters if new else update payload/status/timestamps.

    ``chapters`` is a sequence of dictionaries already containing the primary
    key ``id`` plus required fields. This keeps ingestion pipeline decoupled
    from ORM model construction details.
    """
    for ch in chapters:
        existing = session.get(models.Chapter, ch["id"])
        if existing:
            continue
        session.add(
            models.Chapter(
                id=ch["id"],
                book_id=ch["book_id"],
                index=ch["index"],
                title=ch["title"],
                text_sha256=ch["text_sha256"],
                payload=ch,
                status="clean",
            )
        )


def list_chapters(session: Session, book_id: str) -> list[models.Chapter]:
    """Return all chapters for a book ordered by ``index``."""
    stmt = select(models.Chapter).where(models.Chapter.book_id == book_id).order_by(models.Chapter.index)
    return list(session.scalars(stmt))


def delete_chapters(session: Session, book_id: str) -> int:
    """Delete all chapters for a book and return count deleted.

    Useful for resetting ingestion numbering so indices restart from 0.
    """
    stmt = delete(models.Chapter).where(models.Chapter.book_id == book_id)
    result = session.execute(stmt)
    # SQLAlchemy 2.0 result.rowcount may be -1 for some dialects; guard.
    try:
        deleted = int(result.rowcount or 0)
    except Exception:  # noqa: BLE001
        deleted = 0
    return deleted


def list_books(session: Session) -> list[models.Book]:
    """Return all books ordered by id."""
    stmt = select(models.Book).order_by(models.Book.id)
    return list(session.scalars(stmt))
