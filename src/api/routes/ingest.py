"""Ingestion endpoints and helpers for Auto Audiobook Maker API.

Implements:
- POST /ingest: single PDF ingest by stored name or uploaded file
- POST /books/{book_id}/pdfs: upload one or more PDFs into data/books/{book}/source_pdfs
- POST /ingest_multi_pdf: ingest a zip archive containing PDFs as separate chapters
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from db import get_session, repository
from pipeline.ingestion.core import enumerate_pdfs, extract_and_chapterize
from pipeline.ingestion.multi_pdf import ingest_pdf_files

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
        chunking (bool | None): Whether chunking was used.
        chunk_size (int | None): Chunk size if chunking.
        chunk_count (int | None): Chunk count if chunking.
        parse_mode (str | None): Parse mode used.
        volume_json_path (str | None): Path to volume JSON (single ingest).
        volume_json_paths (list[str] | None): Paths to volume JSONs (batch ingest).
        batch_details (list[dict[str, Any]] | None): Batch details per PDF.
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
    chunking: bool | None = None
    chunk_size: int | None = None
    chunk_count: int | None = None
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
async def ingest(  # noqa: B008 - FastAPI requires param marker calls in defaults
    book_id: str = Form(...),
    file: UploadFile | None = File(None),  # noqa: B008
    pdf_name: str | None = Form(None),
    verbose: int = Form(0),
) -> IngestResponse:
    """Ingest uploaded or stored PDF(s) into chapters (single or batch).

            try:
                payload_text = (
                    Path(ch.json_path).read_text(encoding="utf-8")
                )
                payload_obj = json.loads(payload_text)
    IngestResponse: Ingestion result summary.
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
        # Batch mode: enumerate existing PDFs for book
        pdfs = enumerate_pdfs(book_id)
        if not pdfs:
            raise HTTPException(status_code=400, detail="Must provide file or pdf_name")
        # Perform multi ingest but return aggregate summary
        ingested = ingest_pdf_files(book_id, pdfs, out_root=Path("data/clean"))
        with get_session() as session:
            repository.upsert_book(session, book_id)
            # Persist newly created chapters
            recs: list[dict[str, Any]] = []
            for ch in ingested:
                # Load text from JSON to include in payload
                try:
                    payload_text = Path(ch.json_path).read_text(encoding="utf-8")
                    payload_obj = json.loads(payload_text)
                    payload_text_val = payload_obj.get("text", "")
                except Exception:
                    payload_text_val = ""
                recs.append(
                    {
                        "id": ch.id,
                        "book_id": book_id,
                        "index": ch.index,
                        "title": ch.title,
                        "text_sha256": ch.text_sha256,
                        "json_path": str(ch.json_path),
                        "chapter_id": f"{ch.index:05d}",
                        "source_pdf_name": Path(ch.path).name,
                        "source_pdf": str(ch.path),
                        "meta": {},
                        "text": payload_text_val,
                    }
                )
            repository.store_chapters(session, recs)
            session.commit()
        return IngestResponse(book_id=book_id, chapters=len(ingested), volume_json_path=None)

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
        chunked,
        chunk_size,
        chunk_count,
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
        chunking=chunked,
        chunk_size=chunk_size,
        chunk_count=chunk_count,
        parse_mode=parse_mode,
        volume_json_path=vol_json,
    )


@router.post("/ingest_multi_pdf")
async def ingest_multi_pdf(book_id: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
    """Accept a zip archive of PDFs and ingest each as a chapter."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip archives are supported")
    data = file.file.read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    tmp_dir = Path("data/tmp_zip") / book_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in zf.namelist():
        if name.lower().endswith(".pdf"):
            out = tmp_dir / Path(name).name
            out.write_bytes(zf.read(name))
            paths.append(out)
    if not paths:
        raise HTTPException(status_code=400, detail="Zip contained no PDFs")
    ingested = ingest_pdf_files(book_id, paths, out_root=Path("data/clean"))
    with get_session() as session:
        repository.upsert_book(session, book_id)
        recs: list[dict[str, Any]] = []
        for c in ingested:
            try:
                payload_obj = json.loads(Path(c.json_path).read_text(encoding="utf-8"))
                payload_text_val = payload_obj.get("text", "")
            except Exception:
                payload_text_val = ""
            recs.append(
                {
                    "id": f"{book_id}-{c.index:05d}",
                    "book_id": book_id,
                    "index": c.index,
                    "title": c.title,
                    "text_sha256": c.text_sha256,
                    "json_path": str(c.json_path),
                    "chapter_id": f"{c.index:05d}",
                    "source_pdf_name": Path(c.path).name,
                    "source_pdf": str(c.path),
                    "meta": {},
                    "text": payload_text_val,
                }
            )
        repository.store_chapters(session, recs)
        session.commit()
    return {"book_id": book_id, "chapters": len(ingested)}


@router.post("/books/{book_id}/ingest_pdfs")
async def ingest_book_pdfs(book_id: str) -> dict[str, Any]:
    """Ingest all PDFs for a book from both roots, returning summary."""
    pdfs = enumerate_pdfs(book_id)
    if not pdfs:
        raise HTTPException(status_code=400, detail="No PDFs to ingest")
    ingested = ingest_pdf_files(book_id, pdfs, out_root=Path("data/clean"))
    with get_session() as session:
        repository.upsert_book(session, book_id)
        recs: list[dict[str, Any]] = []
        for c in ingested:
            try:
                payload_obj = json.loads(Path(c.json_path).read_text(encoding="utf-8"))
                payload_text_val = payload_obj.get("text", "")
            except Exception:
                payload_text_val = ""
            recs.append(
                {
                    "id": f"{book_id}-{c.index:05d}",
                    "book_id": book_id,
                    "index": c.index,
                    "title": c.title,
                    "text_sha256": c.text_sha256,
                    "json_path": str(c.json_path),
                    "chapter_id": f"{c.index:05d}",
                    "source_pdf_name": Path(c.path).name,
                    "source_pdf": str(c.path),
                    "meta": {},
                    "text": payload_text_val,
                }
            )
        repository.store_chapters(session, recs)
        session.commit()
    return {"book_id": book_id, "chapters": len(ingested), "pdfs": [p.name for p in pdfs]}
