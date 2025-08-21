"""Job management endpoints for Auto Audiobook Maker API.

This module handles background ingest jobs and job status queries.
"""

import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException

from db import get_session, models, repository
from pipeline.ingestion.core import enumerate_pdfs, extract_and_chapterize

router = APIRouter()


def _update_job_params(job_id: str, **updates: object) -> None:
    """Merge or replace JSON params for a Job entry in-place.

    Args:
        job_id (str): The job identifier.
        **updates (object): Key-value pairs to update in the job params.

    Returns:
        None

    Raises:
        None
    """
    with get_session() as session:
        job = session.get(models.Job, job_id)
        if not job:
            return
        merged: dict[str, object] = dict(job.params or {})
        merged.update(updates)
        job.params = merged
        session.commit()


def _job_prepare(job_id: str) -> models.Job | None:
    """Prepare a job for execution by updating its status and stage.

    Args:
        job_id (str): The job identifier.

    Returns:
        models.Job | None: The job instance if found, else None.

    Raises:
        None
    """
    with get_session() as session:
        job = session.get(models.Job, job_id)
        if not job:
            return None
        job.status = "running"
        job.stage = "ingesting"
        session.commit()
        return job


def _job_single_pdf(book_id: str, pdf_name: str, job_id: str) -> None:
    """Process a single PDF ingest job.

    Args:
        book_id (str): Book identifier.
        pdf_name (str): PDF file name.
        job_id (str): Job identifier.

    Returns:
        None

    Raises:
        RuntimeError: If the PDF is not found.
    """
    _update_job_params(job_id, total_pdfs=1, processed_pdfs=0, progress=0.0)
    root_pdf = Path("data/books") / book_id / pdf_name
    source_pdf = Path("data/books") / book_id / "source_pdfs" / pdf_name
    if root_pdf.exists():
        pdf_path = root_pdf
    elif source_pdf.exists():
        pdf_path = source_pdf
    else:
        raise RuntimeError("pdf_name not found for job")
    with get_session() as _s:
        existing = repository.list_chapters(_s, book_id)
        next_index = len(existing)
    (
        records,
        next_index,
        _,  # result (unused)
        warns,
        page_ct,
        extraction_ms,
        chapterization_ms,
        chunked,
        chunk_size_val,
        chunk_count,
        parse_mode,
        _,  # volume_json_path (unused)
    ) = extract_and_chapterize(
        book_id,
        pdf_path,
        next_index,
        fallback_on_failure=False,
    )
    if extraction_ms is not None:
        _update_job_params(
            job_id,
            last_extraction_ms=extraction_ms,
            last_chapterization_ms=chapterization_ms,
            last_chunking=chunked,
            last_chunk_size=chunk_size_val,
            last_chunk_count=chunk_count,
            parse_mode=parse_mode,
            last_page_count=page_ct or 0,
        )
    with get_session() as session:
        repository.upsert_book(session, book_id)
        if records:
            repository.store_chapters(session, records)
    _update_job_params(
        job_id,
        processed_pdfs=1,
        progress=1.0,
        chapters=len(records),
        parsing_strategy=parse_mode,
        final_warnings=warns,
    )
    with get_session() as session:
        job = session.get(models.Job, job_id)
        if job:
            job.status = "finished"
            job.stage = "done"
            session.commit()


def _execute_ingest_job(job_id: str, book_id: str, pdf_name: str | None) -> None:
    """Execute an ingest job; if pdf_name is omitted, process all PDFs for the book.

    Args:
        job_id (str): Job identifier.
        book_id (str): Book identifier.
        pdf_name (str): PDF file name.

    Returns:
        None

    Raises:
        None (exceptions are caught and logged)
    """
    try:
        if not _job_prepare(job_id):
            return
        if pdf_name:
            _job_single_pdf(book_id, pdf_name, job_id)
        else:
            # Enumerate PDFs and process all, tracking progress
            pdfs = enumerate_pdfs(book_id)
            total = len(pdfs)
            _update_job_params(job_id, total_pdfs=total, processed_pdfs=0, progress=0.0)
            processed = 0
            total_pages = 0
            processed_pages = 0
            for name in [p.name for p in pdfs]:
                try:
                    _job_single_pdf(book_id, name, job_id)
                    processed += 1
                    # Update pages using last extraction metrics if available
                    with get_session() as s:
                        job = s.get(models.Job, job_id)
                        params = dict(job.params or {}) if job else {}
                        raw = params.get("last_page_count", 0) if params else 0
                        try:
                            tp = int(raw) if isinstance(raw, int | str) else 0
                        except Exception:  # pragma: no cover
                            tp = 0
                        total_pages += tp
                        processed_pages += tp
                except Exception:
                    # Log and continue to next PDF; job remains best-effort for multi-file mode
                    import logging as _logging

                    _logging.getLogger(__name__).exception("ingest_job_error processing pdf=%s", name)
                _update_job_params(
                    job_id,
                    processed_pdfs=processed,
                    progress=(processed / total) if total else 1.0,
                    total_pages=total_pages,
                    processed_pages=processed_pages,
                    progress_pages=(processed_pages / total_pages) if total_pages else 0.0,
                )
        with get_session() as session:
            job = session.get(models.Job, job_id)
            if job:
                job.status = "finished"
                job.stage = "finished"
                session.commit()
    except Exception as e:
        with get_session() as session:
            job = session.get(models.Job, job_id)
            if job:
                job.status = "error"
                job.stage = "error"
                job.params = {"error": str(e)}
                session.commit()


@router.post("/ingest_job")
async def ingest_job(
    background_tasks: BackgroundTasks,
    book_id: str = Form(...),
    pdf_name: str | None = Form(None, description="Optional: PDF file name. If omitted, ingest all for book."),
) -> dict[str, Any]:
    """Enqueue an ingest job. If pdf_name is omitted, all book PDFs are processed.

    Args:
    background_tasks (BackgroundTasks): FastAPI background task manager.
    book_id (str): Book identifier.
    pdf_name (str | None): Optional PDF file name for single ingest.

    Returns:
        dict[str, Any]: Job id and status.

    Raises:
        None
    """
    job_id = f"ingest-{book_id}-{uuid4().hex[:8]}"
    created_at = time.time()
    with get_session() as session:
        session.add(
            models.Job(
                id=job_id,
                type="ingest",
                book_id=book_id,
                stage="queued",
                params={"pdf_name": pdf_name, "created_at": created_at, "progress": 0},
                status="pending",
            )
        )
    background_tasks.add_task(_execute_ingest_job, job_id, book_id, pdf_name)
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    """Return job metadata and params by id or 404 if missing.

    Args:
        job_id (str): Job identifier.

    Returns:
        dict[str, Any]: Job metadata and params.

    Raises:
        HTTPException: If the job is not found.
    """
    with get_session() as session:
        job = session.get(models.Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return {
            "id": job.id,
            "type": job.type,
            "book_id": job.book_id,
            "stage": job.stage,
            "status": job.status,
            "params": job.params,
        }
