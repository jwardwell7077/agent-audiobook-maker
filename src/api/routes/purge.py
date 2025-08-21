"""Purge endpoints for Auto Audiobook Maker API.

This module handles deletion of ingestion artifacts and database rows.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_session, repository

router = APIRouter()


class PurgeRequest(BaseModel):
    """Request model for purge endpoint.

    Attributes:
        book_id (str): Book identifier.
        delete_files (bool): Whether to delete files.
        delete_db (bool): Whether to delete DB rows.
        dry_run (bool): Whether this is a dry run.
    """

    book_id: str
    delete_files: bool = True
    delete_db: bool = True
    dry_run: bool = False


class PurgeResponse(BaseModel):
    """Response model for purge endpoint summarizing deletions.

    Attributes:
        book_id (str): Book identifier.
        deleted_file_count (int): Number of files deleted.
        deleted_db_count (int): Number of DB rows deleted.
        dry_run (bool): Whether this was a dry run.
        warnings (list[str]): List of warnings.
    """

    book_id: str
    deleted_file_count: int
    deleted_db_count: int
    dry_run: bool

    warnings: list[str] = []


def _purge_files(clean_dir: Path, dry_run: bool) -> tuple[int, list[str]]:
    """Delete JSON files in the clean_dir for a book.

    Args:
        clean_dir (Path): Directory containing files to purge.
        dry_run (bool): If True, do not actually delete files.

    Returns:
        tuple[int, list[str]]: (count of deleted files, list of warnings)
    """
    count = 0
    warnings: list[str] = []
    if not clean_dir.exists():
        warnings.append("clean_dir_missing")
        return 0, warnings
    for p in clean_dir.glob("*.json"):
        if p.is_file():
            count += 1
            if not dry_run:
                try:
                    p.unlink()
                except Exception as e:
                    warnings.append(f"file_delete_failed:{p.name}:{e}")
    return count, warnings


def _purge_db(book_id: str, dry_run: bool) -> tuple[int, list[str]]:
    """Delete DB rows for a book's chapters.

    Args:
        book_id (str): Book identifier.
        dry_run (bool): If True, do not actually delete DB rows.

    Returns:
        tuple[int, list[str]]: (count of deleted DB rows, list of warnings)
    """
    warnings: list[str] = []
    try:
        with get_session() as session:
            if dry_run:
                return len(repository.list_chapters(session, book_id)), warnings
            deleted = repository.delete_chapters(session, book_id)
            return deleted, warnings
    except Exception as e:
        warnings.append(f"db_delete_failed:{e}")
        return 0, warnings


@router.post("/purge", response_model=PurgeResponse)
async def purge(body: PurgeRequest) -> PurgeResponse:
    """Purge ingestion artifacts for a book (files and/or DB rows).

    Args:
        body (PurgeRequest): Request body with book_id, delete_files, delete_db, dry_run.

    Returns:
        PurgeResponse: Summary of purge operation.

    Raises:
        HTTPException: If book_id is missing.
    """
    warnings: list[str] = []
    book_id = body.book_id
    if not book_id:
        raise HTTPException(status_code=400, detail="book_id required")
    delete_files = body.delete_files
    delete_db = body.delete_db
    dry_run = body.dry_run
    clean_dir = Path("data/clean") / book_id
    file_count = 0
    db_count = 0
    if delete_files:
        fc, file_warnings = _purge_files(clean_dir, dry_run)
        file_count += fc
        warnings.extend(file_warnings)
    if delete_db:
        dc, db_warnings = _purge_db(book_id, dry_run)
        db_count += dc
        warnings.extend(db_warnings)
    return PurgeResponse(
        book_id=book_id,
        deleted_file_count=file_count,
        deleted_db_count=db_count,
        dry_run=dry_run,
        warnings=warnings,
    )
