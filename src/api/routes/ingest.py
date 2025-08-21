"""Ingestion endpoints and helpers for Auto Audiobook Maker API.

Implements:
- POST /ingest: single PDF ingest by stored name or uploaded file
- POST /books/{book_id}/pdfs: upload one or more PDFs into data/books/{book}/source_pdfs
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from db import get_session, repository
from pipeline.ingestion.core import enumerate_pdfs, extract_and_chapterize

router = APIRouter()


class IngestResponse(BaseModel):
    """Response model for ingest endpoints (single or batch).

    Attributes:
        book_id (str): Book identifier.
        chapters (int): Number of chapters ingested.
        backend (str | None): Backend used for ingestion.
        warnings (list[str]): List of warnings.
        page_count (int | None): Number of pages.
        available_backends (list[str] | None): Available backends.
        parsing_strategy (str | None): Parsing strategy used.
        extraction_ms (float | None): Extraction time in ms.
        chapterization_ms (float | None): Chapterization time in ms.
        parse_mode (str | None): Parse mode used.
        volume_json_path (str | None): Path to volume JSON (single ingest).
    """

    book_id: str
    chapters: int
    backend: str | None = None
    warnings: list[str] = []
    page_count: int | None = None
    available_backends: list[str] | None = None
    parsing_strategy: str | None = None
    extraction_ms: float | None = None
    chapterization_ms: float | None = None
    parse_mode: str | None = None
    volume_json_path: str | None = None
    # Note: available_backends duplicated field removed; PyDantic will validate remaining ones


def _save_upload(book_id: str, file: UploadFile) -> Path:
    book_dir = Path("data/books") / book_id / "source_pdfs"
    book_dir.mkdir(parents=True, exist_ok=True)
    fname = file.filename or "upload.pdf"
    dest = book_dir / Path(fname).name
    data = file.file.read()
    dest.write_bytes(data)
    return dest


@router.post("/books/{book_id}/pdfs")
async def upload_book_pdfs(book_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:  # noqa: B008
    """Upload one or more PDF files for a book into source_pdfs."""
    saved: list[str] = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Invalid file type")
        dest = _save_upload(book_id, f)
        saved.append(dest.name)
    return {"book_id": book_id, "saved": saved}


@router.get("/books/{book_id}/pdfs")
async def list_book_pdfs(book_id: str) -> dict[str, Any]:
    """List available PDFs for a book from both roots (root and source_pdfs)."""
    root_dir = Path("data/books") / book_id
    source_dir = root_dir / "source_pdfs"
    pdfs: list[Path] = []
    if root_dir.exists():
        pdfs.extend(sorted(root_dir.glob("*.pdf")))
    if source_dir.exists():
        pdfs.extend(sorted(source_dir.glob("*.pdf")))
    return {
        "book_id": book_id,
        "pdfs": [{"name": p.name, "path": str(p)} for p in pdfs],
    }


@router.post("/ingest", response_model=IngestResponse)
async def ingest(  # noqa: B008, C901, PLR0915 - FastAPI params + pragmatic complexity for endpoint
    book_id: str = Form(...),
    file: UploadFile | None = File(None),  # noqa: B008
    pdf_name: str | None = Form(None),
    verbose: int = Form(0),
) -> IngestResponse:
    """Ingest a single uploaded or stored PDF into chapters.

    Returns an IngestResponse summary including chapter count and timing.
    """
    # Resolve source PDF path
    pdf_path: Path | None = None
    if pdf_name:
        # Look in both roots
        root_pdf = Path("data/books") / book_id / pdf_name
        source_pdf = Path("data/books") / book_id / "source_pdfs" / pdf_name
        if root_pdf.exists():
            pdf_path = root_pdf
        elif source_pdf.exists():
            pdf_path = source_pdf
        else:
            raise HTTPException(status_code=404, detail="pdf_name not found")
    elif file is not None:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only .pdf files supported")
        pdf_path = _save_upload(book_id, file)
        pdf_name = Path(file.filename).name
    else:
        # Batch mode: ingest all PDFs under data/books/<book_id> and source_pdfs

        pdfs = enumerate_pdfs(book_id)
        if not pdfs:
            raise HTTPException(status_code=400, detail="Must provide file or pdf_name")
        total_records = 0
        with get_session() as session:
            repository.upsert_book(session, book_id)
            existing = repository.list_chapters(session, book_id)
            next_index = len(existing)
            skip_titles = [r.title for r in existing]
        volume_json_path: str | None = None
        warns_all: list[str] = []
        last_backend: str | None = None
        extraction_ms = None
        chapterization_ms = None
        for path in pdfs:
            (
                records,
                next_index,
                result,
                warns,
                _page_ct,
                extraction_ms,
                chapterization_ms,
                _parse_mode,
                vol_json,
            ) = extract_and_chapterize(
                book_id,
                path,
                next_index,
                skip_if=skip_titles,
                fallback_on_failure=True,
            )
            with get_session() as session:
                if records:
                    repository.store_chapters(session, records)
                    session.commit()
            total_records += len(records)
            warns_all.extend(warns)
            last_backend = getattr(result, "backend", None) and getattr(result.backend, "value", None)
            if vol_json:
                volume_json_path = vol_json
        return IngestResponse(
            book_id=book_id,
            chapters=total_records,
            backend=last_backend,
            warnings=warns_all,
            page_count=None,
            parsing_strategy="structured_toc",
            extraction_ms=extraction_ms,
            chapterization_ms=chapterization_ms,
            volume_json_path=volume_json_path,
        )

    # Single-PDF ingest path
    # pdf_path must be resolved by now
    with get_session() as session:
        repository.upsert_book(session, book_id)
        existing = repository.list_chapters(session, book_id)
        next_index = len(existing)
        skip_titles = [r.title for r in existing]
    (
        records,
        next_index,
        result,
        warns,
        page_ct,
        extraction_ms,
        chapterization_ms,
        parse_mode,
        vol_json,
    ) = extract_and_chapterize(  # noqa: E501
        book_id,
        pdf_path,
        next_index,
        skip_if=skip_titles,
        fallback_on_failure=False,
    )
    # Persist
    with get_session() as session:
        if records:
            repository.store_chapters(session, records)
            session.commit()
    return IngestResponse(
        book_id=book_id,
        chapters=len(records),
        backend=getattr(result, "backend", None) and getattr(result.backend, "value", None),
        warnings=warns,
        page_count=page_ct,
        parsing_strategy=parse_mode,
        extraction_ms=extraction_ms,
        chapterization_ms=chapterization_ms,
        volume_json_path=vol_json,
    )
    # batch ingestion endpoints removed for simplicity
