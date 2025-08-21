"""Listing endpoints for Auto Audiobook Maker API.

This module handles listing of books, chapters, and PDFs.
"""

from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException

from db import get_session, models, repository

router = APIRouter()


@router.get("/books")
async def list_books() -> list[dict[str, Any]]:
    """List all books (filesystem discovered + DB metadata).

    Returns:
        list[dict[str, Any]]: List of book metadata.
    """
    # Ensure filesystem-discovered books are present
    # _ensure_books_in_db() should be called in app startup or here if needed
    with get_session() as session:
        books = repository.list_books(session)
        return [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "created_at": b.created_at.isoformat(),
            }
            for b in books
        ]


@router.get("/books/{book_id}/chapters")
async def list_book_chapters(book_id: str) -> list[dict[str, Any]]:
    """Return chapter summaries for a book.

    Args:
        book_id (str): Book identifier.

    Returns:
        list[dict[str, Any]]: List of chapter summaries.
    """
    with get_session() as session:
        chapters = repository.list_chapters(session, book_id)
        result_rows: list[dict[str, Any]] = []
        for c in chapters:
            payload = c.payload
            meta = payload.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta = cast(dict[str, Any], meta)
            result_rows.append(
                {
                    "id": c.id,
                    "index": c.index,
                    "title": c.title,
                    "status": c.status,
                    "text_sha256": c.text_sha256,
                    "word_count": meta.get("word_count"),
                    "char_count": meta.get("char_count"),
                    "paragraph_count": meta.get("paragraph_count"),
                    "sentence_count": meta.get("sentence_count"),
                    "source": meta.get("source"),
                }
            )
        return result_rows


@router.get("/books/{book_id}/chapters/{chapter_id}")
async def get_book_chapter_detail(book_id: str, chapter_id: str) -> dict[str, Any]:
    """Return full chapter payload including text and meta.

    Args:
        book_id (str): Book identifier.
        chapter_id (str): Chapter identifier.

    Returns:
        dict[str, Any]: Chapter details including text and meta.

    Raises:
        HTTPException: If chapter is not found.
    """
    with get_session() as session:
        full_id = f"{book_id}-{chapter_id}"
        chapter = session.get(models.Chapter, full_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")
        payload = chapter.payload
        return {
            "id": chapter.id,
            "book_id": book_id,
            "chapter_id": chapter_id,
            "index": chapter.index,
            "title": chapter.title,
            "status": chapter.status,
            "text_sha256": chapter.text_sha256,
            "text": payload.get("text"),
            "meta": payload.get("meta", {}),
            "json_path": payload.get("json_path"),
            "source_pdf": payload.get("source_pdf"),
        }


@router.get("/books/{book_id}/pdfs")
async def list_book_pdfs(book_id: str) -> dict[str, Any]:
    """List all PDF files associated with a given book.

    Args:
        book_id (str): Book identifier.

    Returns:
        dict[str, Any]: Book ID and list of PDFs.
    """
    book_dir = Path("data/books") / book_id
    source_dir = book_dir / "source_pdfs"
    pdfs: list[dict[str, Any]] = []
    if source_dir.exists():
        pdfs.extend([{"name": p.name, "size": p.stat().st_size} for p in sorted(source_dir.glob("*.pdf"))])
    if book_dir.exists():  # root-level pdfs
        pdfs.extend([{"name": p.name, "size": p.stat().st_size} for p in sorted(book_dir.glob("*.pdf"))])
    return {"book_id": book_id, "pdfs": pdfs}


@router.get("/pdfs")
async def list_all_pdfs() -> dict[str, Any]:
    """List all PDF files across every book directory.

    Returns:
        dict[str, Any]: List of books and their PDFs.
    """
    root = Path("data/books")
    if not root.exists():
        return {"books": []}
    results: list[dict[str, Any]] = []
    for bid in [d.name for d in root.iterdir() if d.is_dir()]:
        book_dir = root / bid
        entries: list[dict[str, Any]] = []
        source_dir = book_dir / "source_pdfs"
        if source_dir.exists():
            entries.extend(
                [
                    {
                        "name": f"source_pdfs/{p.name}",
                        "size": p.stat().st_size,
                    }
                    for p in sorted(source_dir.glob("*.pdf"))
                ]
            )
        entries.extend([{"name": p.name, "size": p.stat().st_size} for p in sorted(book_dir.glob("*.pdf"))])
        if entries:
            results.append({"book_id": bid, "pdfs": entries})
    return {"books": results}
