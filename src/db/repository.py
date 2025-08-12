from __future__ import annotations

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models


def upsert_book(
    session: Session,
    book_id: str,
    title: str | None = None,
    author: str | None = None,
) -> models.Book:
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


def store_chapters(session: Session, chapters: Sequence[dict]) -> None:
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
    stmt = (
        select(models.Chapter)
        .where(models.Chapter.book_id == book_id)
        .order_by(models.Chapter.index)
    )
    return list(session.scalars(stmt))


def list_books(session: Session) -> list[models.Book]:
    stmt = select(models.Book).order_by(models.Book.id)
    return list(session.scalars(stmt))
