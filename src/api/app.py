from __future__ import annotations

from fastapi import (
    FastAPI,
    UploadFile,
    Form,
    HTTPException,
    File,
    BackgroundTasks,
)
from pydantic import BaseModel
from fastapi import Body
from pathlib import Path
from typing import List
import re
import zipfile
import io

from pipeline.ingestion.multi_pdf import ingest_pdf_files
from pipeline.ingestion.pdf import detect_available_backends
from pipeline.ingestion.core import (
    extract_and_chapterize,
    enumerate_pdfs,
)
from pipeline.annotation.run import run_annotation_for_chapter
from tts.engines import (
    synthesize_and_render_chapter,
)  # type: ignore  # pylint: disable=import-error
from db import get_session
from db import repository
from uuid import uuid4
import time
from contextlib import asynccontextmanager
from api.logging_setup import get_logger, log_call, setup_logging

# Ensure logging handlers are configured on import
setup_logging()

logger = get_logger(__name__)

 
@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    _ensure_books_in_db()
    yield


app = FastAPI(title="Auto Audiobook Maker API", lifespan=lifespan)


def _discover_book_dirs(root: Path = Path("data/books")) -> list[str]:
    """Return list of book directory names under data/books.

    A directory qualifies if it contains:
    - A source_pdfs/ subdir with any *.pdf OR
    - One or more *.pdf files directly inside it.
    """
    if not root.exists():  # pragma: no cover - empty fresh env
        return []
    books: list[str] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        source_dir = d / "source_pdfs"
        has_source = source_dir.exists() and any(source_dir.glob("*.pdf"))
        has_root_pdfs = any(d.glob("*.pdf"))
        if has_source or has_root_pdfs:
            books.append(d.name)
    return books


def _ensure_books_in_db():  # pragma: no cover - simple coordinator
    from db import repository  # local import to avoid cycles
    from db import get_session

    discovered = _discover_book_dirs()
    if not discovered:
        return
    with get_session() as session:
        for book_id in discovered:
            repository.upsert_book(session, book_id)


# Removed deprecated on_event usage; handled in lifespan


class IngestResponse(BaseModel):
    book_id: str
    chapters: int
    backend: str | None = None
    warnings: List[str] = []
    page_count: int | None = None
    available_backends: List[str] | None = None
    parsing_strategy: str | None = None
    extraction_ms: float | None = None
    chapterization_ms: float | None = None
    chunking: bool | None = None
    chunk_size: int | None = None
    chunk_count: int | None = None
    parse_mode: str | None = None
    volume_json_path: str | None = None  # single ingest
    volume_json_paths: List[str] | None = None  # batch ingest list
    # New: detailed batch entries providing per-PDF warnings & volume path
    batch_details: List[dict] | None = None


class PurgeResponse(BaseModel):
    book_id: str
    deleted_file_count: int
    deleted_db_count: int
    dry_run: bool
    warnings: List[str] = []


def _update_job_params(job_id: str, **updates) -> None:
    """Utility to merge/replace params for a Job entry."""
    from db.models import Job
    with get_session() as session:  # pragma: no cover - small helper
        job = session.get(Job, job_id)
        if not job:
            return
        params = dict(job.params or {})
        params.update(updates)
        job.params = params
        session.commit()


@app.get("/health")
@log_call()
async def health() -> dict:
    return {"status": "ok"}


@app.post("/purge", response_model=PurgeResponse)
@log_call()
async def purge(
    body: dict = Body(...),
) -> PurgeResponse:  # type: ignore[valid-type]
    """Purge ingestion artifacts for a book.

    delete_files: remove data/clean/<book_id>/*.json
    delete_db: delete Chapter rows for book (indices reset on next ingest)
    dry_run: report counts without performing deletions
    """
    warnings: list[str] = []
    book_id = body.get("book_id")
    if not book_id:
        raise HTTPException(status_code=400, detail="book_id required")
    delete_files = bool(body.get("delete_files", True))
    delete_db = bool(body.get("delete_db", True))
    dry_run = bool(body.get("dry_run", False))
    file_count = 0
    db_count = 0
    clean_dir = Path("data/clean") / book_id
    if delete_files:
        if clean_dir.exists():
            for p in clean_dir.glob("*.json"):
                if p.is_file():
                    file_count += 1
                    if not dry_run:
                        try:
                            p.unlink()
                        except Exception as e:  # noqa: BLE001
                            warnings.append(f"file_delete_failed:{p.name}:{e}")
        else:
            warnings.append("clean_dir_missing")
    if delete_db:
        try:
            with get_session() as session:
                if not dry_run:
                    from db import repository as repo  # local import

                    db_count = repo.delete_chapters(session, book_id)
                else:
                    # Count rows
                    from db import repository as repo  # type: ignore
                    chapters = repo.list_chapters(session, book_id)
                    db_count = len(chapters)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"db_delete_failed:{e}")
    return PurgeResponse(
        book_id=book_id,
        deleted_file_count=file_count,
        deleted_db_count=db_count,
        dry_run=dry_run,
        warnings=warnings,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    book_id: str = Form(...),
    file: UploadFile | None = File(None),
    pdf_name: str | None = Form(
        None,
        description=(
            "Optional name of existing PDF under data/books/{book_id} or "
            "data/books/{book_id}/source_pdfs to ingest instead of uploading"
        ),
    ),
    verbose: int | None = Form(
        0,
        description=(
            "Set to 1 to include timing & chunking diagnostics in response"
        ),
    ),
) -> IngestResponse:
    # Modes:
    # 1. file provided -> ingest uploaded PDF
    # 2. pdf_name provided -> ingest a single stored PDF
    # 3. neither provided -> batch ingest all stored PDFs for book
    if not file and not pdf_name:
        # Batch mode
        pdf_paths = enumerate_pdfs(book_id)
        if not pdf_paths:
            raise HTTPException(
                status_code=404,
                detail="no PDFs found for book (root or source_pdfs)",
            )
        logger.info(
            "Batch ingest start book_id=%s pdf_count=%s",
            book_id,
            len(pdf_paths),
        )
        with get_session() as _s:
            existing = repository.list_chapters(_s, book_id)
            next_index = len(existing)
            existing_titles = {c.title for c in existing}
            existing_source_pdf_names = {
                c.payload.get("source_pdf_name")
                for c in existing
                if isinstance(c.payload, dict)
                and c.payload.get("source_pdf_name") is not None
            }
        skip_set = existing_source_pdf_names | existing_titles
        available_backends = [b.value for b in detect_available_backends()]
        total_records: list[dict] = []
        total_warnings: list[str] = []
        parsing_modes: set[str] = set()
        page_count_total = 0
        total_extraction_ms = 0.0
        total_chapterization_ms = 0.0
        chunking_used = False
        chunk_size_used: int | None = None
        chunk_count_total = 0
        volume_paths: list[str] = []
        batch_details: list[dict] = []
        for pdf_path in pdf_paths:
            (
                records,
                next_index,
                result,
                warns,
                page_ct,
                extraction_ms,
                chapterization_ms,
                chunked,
                chunk_size_val,
                chunk_count,
                parse_mode,
                volume_json_path,
            ) = extract_and_chapterize(
                book_id, pdf_path, next_index, skip_if=skip_set
            )
            total_records.extend(records)
            if volume_json_path:
                volume_paths.append(volume_json_path)
            batch_details.append(
                {
                    "pdf_name": pdf_path.name,
                    "new_chapters": len(records),
                    "warnings": warns,
                    "parse_mode": parse_mode,
                    "volume_json_path": volume_json_path,
                    "page_count": page_ct,
                }
            )
            page_count_total += page_ct
            total_warnings.extend(warns)
            total_extraction_ms += extraction_ms or 0.0
            total_chapterization_ms += chapterization_ms or 0.0
            if chunked:
                chunking_used = True
                chunk_size_used = chunk_size_val
                chunk_count_total += chunk_count or 0
            if result is not None and result.text and parse_mode:
                parsing_modes.add(parse_mode)
        with get_session() as session:
            repository.upsert_book(session, book_id)
            repository.store_chapters(session, total_records)
        logger.info(
            "Batch ingest complete book_id=%s new_chapters=%s warnings=%s",
            book_id,
            len(total_records),
            len(total_warnings),
        )
        return IngestResponse(
            book_id=book_id,
            chapters=len(total_records),
            backend="batch",
            warnings=total_warnings,
            page_count=page_count_total or None,
            available_backends=available_backends,
            parsing_strategy=":".join(sorted(parsing_modes))
            if parsing_modes
            else None,
            extraction_ms=total_extraction_ms if verbose else None,
            chapterization_ms=total_chapterization_ms if verbose else None,
            chunking=chunking_used if verbose else None,
            chunk_size=chunk_size_used if verbose else None,
            chunk_count=(
                chunk_count_total if (verbose and chunking_used) else None
            ),
            parse_mode=(
                ":".join(sorted(parsing_modes)) if parsing_modes else None
            ),
            volume_json_path=None,
            volume_json_paths=volume_paths or None,
            batch_details=batch_details or None,
        )
    # Resolve input: either uploaded file bytes or an existing stored PDF
    if pdf_name:
        # Search both root and source_pdfs
        root_pdf = Path("data/books") / book_id / pdf_name
        source_pdf = Path("data/books") / book_id / "source_pdfs" / pdf_name
        if root_pdf.exists():
            tmp_path = root_pdf
            name_lower = root_pdf.name.lower()
            raw_bytes = root_pdf.read_bytes()
        elif source_pdf.exists():
            tmp_path = source_pdf
            name_lower = source_pdf.name.lower()
            raw_bytes = source_pdf.read_bytes()
        else:
            raise HTTPException(status_code=404, detail="pdf_name not found")
    else:
        raw_bytes = await file.read()  # type: ignore
        name_lower = (
            file.filename.lower() if file and file.filename else ""
        )  # type: ignore
        tmp_path = None
    # Use unified structured-only pipeline
    if not name_lower.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF ingest supported now"
        )
    if tmp_path is None:
        tmp_path = Path("/tmp") / (
            (file.filename if file and file.filename else "upload.pdf")
        )  # type: ignore
        tmp_path.write_bytes(raw_bytes)
    # Run pipeline (next index = existing chapter count)
    with get_session() as _s:
        existing = repository.list_chapters(_s, book_id)
        next_index = len(existing)
        # Capture needed fields before session closes to avoid detached access
        existing_titles = {c.title for c in existing}
        existing_ids = {f"{book_id}-{c.id}" for c in existing}
    skip_if = existing_titles | existing_ids
    (
        records,
        _next_index,
        result,
        warns,
        page_ct,
        extraction_ms,
        chapterization_ms,
        chunked,
        chunk_size_val,
        chunk_count,
        parse_mode,
        volume_json_path,
    ) = extract_and_chapterize(book_id, tmp_path, next_index, skip_if=skip_if)
    with get_session() as session:
        repository.upsert_book(session, book_id)
        if records:
            repository.store_chapters(session, records)
    available_backends = [b.value for b in detect_available_backends()]
    return IngestResponse(
        book_id=book_id,
        chapters=len(records),
        backend=(result.backend.value if result else None),
        warnings=warns,
        page_count=page_ct,
        available_backends=available_backends,
        parsing_strategy=parse_mode,
        extraction_ms=extraction_ms if verbose else None,
        chapterization_ms=chapterization_ms if verbose else None,
        chunking=chunked if verbose else None,
        chunk_size=chunk_size_val if verbose else None,
        chunk_count=chunk_count if (verbose and chunked) else None,
        parse_mode=parse_mode,
        volume_json_path=volume_json_path,
    )


@app.post("/ingest_job")
async def ingest_job(
    background_tasks: BackgroundTasks,  # injected by FastAPI
    book_id: str = Form(...),
    pdf_name: str | None = Form(
        None, description="Optional specific stored PDF (else batch ingest)"
    ),
) -> dict:
    """Enqueue an ingest job (batch or single stored PDF).

    Returns job_id immediately; poll /jobs/{job_id} for status.
    """
    job_id = f"ingest-{book_id}-{uuid4().hex[:8]}"
    created_at = time.time()
    with get_session() as session:
        from db.models import Job

        session.add(
            Job(
                id=job_id,
                type="ingest",
                book_id=book_id,
                stage="queued",
                params={
                    "pdf_name": pdf_name,
                    "created_at": created_at,
                    "progress": 0,
                },
                status="pending",
            )
        )

    def _run():  # pragma: no cover - background execution
        from db.models import Job
        logger.info(
            "Job start job_id=%s book_id=%s pdf_name=%s",
            job_id,
            book_id,
            pdf_name,
        )
        try:
            with get_session() as session:
                job = session.get(Job, job_id)
                if not job:
                    return
                job.status = "running"
                job.stage = "ingesting"
                session.commit()
            # Batch mode progress-aware ingestion
            if not pdf_name:
                pdf_paths = enumerate_pdfs(book_id)
                total = len(pdf_paths)
                if not pdf_paths:
                    raise RuntimeError("no PDFs found for batch ingest job")
                _update_job_params(
                    job_id,
                    total_pdfs=total,
                    processed_pdfs=0,
                    progress=0.0,
                    total_pages=0,
                    processed_pages=0,
                    progress_pages=0.0,
                )
                new_chapter_total = 0
                warnings_all: list[str] = []
                with get_session() as _s:
                    existing = repository.list_chapters(_s, book_id)
                    next_index = len(existing)
                    existing_titles = {c.title for c in existing}
                    existing_source_pdf_names = {
                        c.payload.get("source_pdf_name")
                        for c in existing
                        if isinstance(c.payload, dict)
                        and c.payload.get("source_pdf_name") is not None
                    }
                total_pages = 0
                processed_pages = 0
                skip_set = existing_source_pdf_names | existing_titles
                for idx, pdf_path in enumerate(pdf_paths, start=1):
                    _update_job_params(
                        job_id,
                        current_pdf=pdf_path.name,
                        processed_pdfs=idx - 1,
                        progress=float(idx - 1) / float(total),
                    )
                    (
                        records,
                        next_index,
                        result,
                        warns,
                        page_ct,
                        extraction_ms,
                        chapterization_ms,
                        chunked,
                        chunk_size_val,
                        chunk_count,
                        parse_mode,
                        volume_json_path,
                    ) = extract_and_chapterize(
                        book_id,
                        pdf_path,
                        next_index,
                        skip_if=skip_set,
                    )
                    warnings_all.extend(warns)
                    if result is None:
                        continue
                    if extraction_ms is not None:
                        _update_job_params(
                            job_id,
                            last_extraction_ms=extraction_ms,
                            last_chapterization_ms=chapterization_ms,
                            last_chunking=chunked,
                            last_chunk_size=chunk_size_val,
                            last_chunk_count=chunk_count,
                            parse_mode=parse_mode,
                            last_volume_json_path=volume_json_path,
                        )
                    total_pages += page_ct
                    _update_job_params(
                        job_id,
                        total_pages=total_pages,
                        processed_pages=processed_pages,
                        progress_pages=(
                            float(processed_pages) / total_pages
                            if total_pages
                            else 0.0
                        ),
                    )
                    # Simulate per-page progress
                    for _pg in result.pages:
                        processed_pages += 1
                        _update_job_params(
                            job_id,
                            processed_pages=processed_pages,
                            progress_pages=(
                                float(processed_pages) / total_pages
                                if total_pages
                                else 0.0
                            ),
                        )
                    if records:
                        with get_session() as session:
                            repository.upsert_book(session, book_id)
                            repository.store_chapters(session, records)
                        new_chapter_total += len(records)
                    _update_job_params(
                        job_id,
                        processed_pdfs=idx,
                        progress=float(idx) / float(total),
                    )
                _update_job_params(
                    job_id,
                    final_warnings=warnings_all,
                    new_chapters=new_chapter_total,
                )
            else:  # single stored PDF ingestion (structured only)
                _update_job_params(
                    job_id,
                    total_pdfs=1,
                    processed_pdfs=0,
                    progress=0.0,
                )
                root_pdf = Path("data/books") / book_id / pdf_name
                source_pdf = (
                    Path("data/books") / book_id / "source_pdfs" / pdf_name
                )
                pdf_path: Path
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
                    result,
                    warns,
                    page_ct,
                    extraction_ms,
                    chapterization_ms,
                    chunked,
                    chunk_size_val,
                    chunk_count,
                    parse_mode,
                    volume_json_path,
                ) = extract_and_chapterize(
                    book_id, pdf_path, next_index
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
                job = session.get(Job, job_id)
                if job:
                    job.status = "finished"
                    job.stage = "done"
                    session.commit()
            logger.info("Job finished job_id=%s book_id=%s", job_id, book_id)
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "Job error job_id=%s book_id=%s error=%s", job_id, book_id, e
            )
            with get_session() as session:
                job = session.get(Job, job_id)
                if job:
                    job.status = "error"
                    job.stage = "error"
                    job.params = {"error": str(e)}
                    session.commit()

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
@log_call()
async def get_job(job_id: str) -> dict:
    from db.models import Job

    with get_session() as session:
        job = session.get(Job, job_id)
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


@app.post("/ingest_multi_pdf")
async def ingest_multi_pdf(
    book_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    """Ingest a zip containing per-chapter PDF files.

    Returns summary: book_id, chapters (count), files list.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="zip file required")
    raw = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="invalid zip archive")
    pdf_members = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
    if not pdf_members:
        raise HTTPException(status_code=400, detail="no pdfs in archive")
    tmp_dir = Path("/tmp") / f"ingest_{book_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in pdf_members:
        target = tmp_dir / Path(name).name
        with target.open("wb") as f:
            f.write(zf.read(name))
        paths.append(target)
    chapters = ingest_pdf_files(book_id, paths, out_root=Path("data/clean"))
    with get_session() as session:
        repository.upsert_book(session, book_id)
        repository.store_chapters(
            session,
            [
                {
                    "id": f"{book_id}-{c.index:05d}",
                    "book_id": book_id,
                    "index": c.index,
                    "title": c.title,
                    "text_sha256": c.text_sha256,
                    # Load per‑chapter JSON (authoritative text) parse &
                    # compute lightweight metadata
                    **(
                        lambda payload: {
                            "text": payload.get("text", ""),
                            "meta": {
                                "source": "multi_pdf",
                                "word_count": (
                                    len(
                                        re.findall(
                                            r"\\b\\w+\\b",
                                            payload.get("text", ""),
                                        )
                                    )
                                    if payload.get("text")
                                    else 0
                                ),
                                "char_count": len(payload.get("text", "")),
                                "paragraph_count": (
                                    len(
                                        [
                                            p
                                            for p in payload.get(
                                                "text", ""
                                            ).split("\n\n")
                                            if p.strip()
                                        ]
                                    )
                                    if payload.get("text")
                                    else 0
                                ),
                                "sentence_count": (
                                    len(
                                        [
                                            s
                                            for s in re.split(
                                                r"(?<=[.!?])\\s+",
                                                payload.get(
                                                    "text", ""
                                                ).strip(),
                                            )
                                            if s
                                        ]
                                    )
                                    if payload.get("text")
                                    else 0
                                ),
                            },
                        }
                    )(
                        (
                            __import__("json").loads(
                                c.json_path.read_text(
                                    encoding="utf-8"
                                )
                            )
                        )
                        if c.json_path.exists()
                        else {"text": ""}
                    ),
                    "json_path": str(c.json_path),
                    "source_pdf": str(c.path),
                }
                for c in chapters
            ],
        )
    return {
        "book_id": book_id,
        "chapters": len(chapters),
        "files": [p.name for p in paths],
    }


@app.post("/books/{book_id}/pdfs")
async def upload_book_pdfs(
    book_id: str,
    files: List[UploadFile] = File(...),
) -> dict:
    """Upload one or more PDF files into a managed source directory.

    Stored under data/books/{book_id}/source_pdfs preserving filename.
    """
    if not files:
        raise HTTPException(status_code=400, detail="no files provided")
    source_dir = Path("data/books") / book_id / "source_pdfs"
    source_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for uf in files:
        if not uf.filename or not uf.filename.lower().endswith(".pdf"):
            continue
        content = await uf.read()
        (source_dir / uf.filename).write_bytes(content)
        saved.append(uf.filename)
    if not saved:
        raise HTTPException(status_code=400, detail="no valid pdf files")
    return {"book_id": book_id, "saved": saved}


@app.get("/books/{book_id}/pdfs")
@log_call()
async def list_book_pdfs(book_id: str) -> dict:
    book_dir = Path("data/books") / book_id
    source_dir = book_dir / "source_pdfs"
    pdfs: list[dict] = []
    if source_dir.exists():
        pdfs.extend(
            [
                {"name": p.name, "size": p.stat().st_size}
                for p in sorted(source_dir.glob("*.pdf"))
            ]
        )
    if book_dir.exists():  # root-level pdfs
        pdfs.extend(
            [
                {"name": p.name, "size": p.stat().st_size}
                for p in sorted(book_dir.glob("*.pdf"))
            ]
        )
    return {"book_id": book_id, "pdfs": pdfs}


@app.get("/pdfs")
@log_call()
async def list_all_pdfs() -> dict:
    """List all PDF files across every book directory.

    Includes both source_pdfs/ subdirectory PDFs and root-level PDFs.
    Also ensures any discovered book directories are upserted into DB.
    """
    _ensure_books_in_db()
    root = Path("data/books")
    if not root.exists():
        return {"books": []}
    results: list[dict] = []
    for book_id in _discover_book_dirs(root):
        book_dir = root / book_id
        entries: list[dict] = []
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
        entries.extend(
            [
                {"name": p.name, "size": p.stat().st_size}
                for p in sorted(book_dir.glob("*.pdf"))
            ]
        )
        if entries:
            results.append({"book_id": book_id, "pdfs": entries})
    return {"books": results}


@app.post("/books/{book_id}/ingest_pdfs")
@log_call()
async def ingest_stored_pdfs(book_id: str) -> dict:
    """Ingest all stored source PDFs for a book (per-chapter PDFs).

    Looks at data/books/{book_id}/source_pdfs/*.pdf, runs multi_pdf
    ingestion, persists chapters & returns summary.
    """
    source_dir = Path("data/books") / book_id / "source_pdfs"
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="no source_pdfs dir")
    pdfs = sorted(source_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(status_code=400, detail="no pdf files found")
    chapters = ingest_pdf_files(book_id, pdfs, out_root=Path("data/clean"))
    # Persist in DB if not already
    with get_session() as session:
        repository.upsert_book(session, book_id)
        repository.store_chapters(
            session,
            [
                {
                    "id": f"{book_id}-{c.index:05d}",
                    "book_id": book_id,
                    "index": c.index,
                    "title": c.title,
                    "text_sha256": c.text_sha256,
                    "json_path": str(c.json_path),
                    "source_pdf": str(c.path),
                    "meta": {"source": "multi_pdf"},
                }
                for c in chapters
            ],
        )
    return {
        "book_id": book_id,
        "chapters": len(chapters),
        "pdfs": [p.name for p in pdfs],
    }


@app.get("/books")
@log_call()
async def list_books() -> list[dict]:
    # Ensure filesystem-discovered books are present
    _ensure_books_in_db()
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


@app.get("/books/{book_id}/chapters")
@log_call()
async def list_book_chapters(book_id: str) -> list[dict]:
    with get_session() as session:
        chapters = repository.list_chapters(session, book_id)
        return [
            {
                "id": c.id,
                "index": c.index,
                "title": c.title,
                "status": c.status,
                "text_sha256": c.text_sha256,
                # Provide summary metadata if available
                **(
                    {
                        "word_count": c.payload.get("meta", {}).get(
                            "word_count"
                        ),
                        "char_count": c.payload.get("meta", {}).get(
                            "char_count"
                        ),
                        "paragraph_count": c.payload.get("meta", {}).get(
                            "paragraph_count"
                        ),
                        "sentence_count": c.payload.get("meta", {}).get(
                            "sentence_count"
                        ),
                        "source": c.payload.get("meta", {}).get(
                            "source"
                        ),
                    }
                    if isinstance(c.payload, dict)
                    else {}
                ),
            }
            for c in chapters
        ]


@app.get("/books/{book_id}/chapters/{chapter_id}")
@log_call()
async def get_book_chapter_detail(book_id: str, chapter_id: str) -> dict:
    """Return full chapter payload including text and meta.

    chapter_id is the zero-padded internal chapter id (e.g. 00000).
    """
    with get_session() as session:
        full_id = f"{book_id}-{chapter_id}"
        chapter = session.get(repository.models.Chapter, full_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")
        payload = chapter.payload if isinstance(chapter.payload, dict) else {}
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


@app.get("/chapters/{book_id}/{chapter_id}/annotations")
@log_call()
async def get_chapter_annotations(
    book_id: str,
    chapter_id: str,
    force: bool = False,
    enable_coref: bool = True,
    enable_emotion: bool = True,
    enable_qa: bool = True,
    max_segments: int = 200,
) -> dict:
    """Fetch or compute annotations for a chapter.

    Query params allow overriding flags; set force=true to recompute.
    """
    # verify chapter exists
    with get_session() as session:
        chapter = session.get(
            repository.models.Chapter, f"{book_id}-{chapter_id}"
        )
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")
    result = await run_annotation_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        force=force,
        enable_coref=enable_coref,
        enable_emotion=enable_emotion,
        enable_qa=enable_qa,
        max_segments=max_segments,
    )
    return result


@app.post("/chapters/{book_id}/{chapter_id}/render")
@log_call()
async def render_chapter(
    book_id: str,
    chapter_id: str,
    force: bool = False,
    prefer_xtts: bool = True,
) -> dict:
    """Trigger (or fetch existing) chapter render.

    If a render row already exists and force is False, returns its metadata
    without recomputing. Otherwise synthesizes stems and stitches.
    """
    # Verify chapter exists and load annotations for segments
    with get_session() as session:
        chapter_key = f"{book_id}-{chapter_id}"
        chapter = session.get(repository.models.Chapter, chapter_key)
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")
        render_id = f"{book_id}-{chapter_id}-render"
        existing = session.get(repository.models.Render, render_id)
        if existing and not force:
            return {
                "render_path": existing.path,
                "loudness_lufs": existing.loudness_lufs,
                "peak_dbfs": existing.peak_dbfs,
                "duration_s": existing.duration_s,
                "status": existing.status,
                "stem_count": None,
                "elapsed_s": None,
            }
    # Need segments: pull annotations (compute if missing)
    ann = await get_chapter_annotations(book_id, chapter_id, force=False)
    segments = ann.get("segments", [])
    meta = synthesize_and_render_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        segments=segments,
        prefer_xtts=prefer_xtts,
    )
    return meta
