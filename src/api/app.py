from __future__ import annotations

from fastapi import FastAPI, UploadFile, Form, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import List

from src.pipeline.ingestion.chapterizer import (
    simple_chapterize,
    write_chapter_json,
)
from src.pipeline.ingestion.pdf import (
    extract_pdf_text,
    detect_available_backends,
)
from src.pipeline.annotation.run import run_annotation_for_chapter
from tts.engines import (
    synthesize_and_render_chapter,
)  # type: ignore  # pylint: disable=import-error
from src.db import get_session
from src.db import repository

app = FastAPI(title="Auto Audiobook Maker API")


class IngestResponse(BaseModel):
    book_id: str
    chapters: int
    backend: str | None = None
    warnings: List[str] = []
    page_count: int | None = None
    available_backends: List[str] | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    book_id: str = Form(...),
    file: UploadFile | None = None,
) -> IngestResponse:
    if not file:
        raise ValueError("file required")
    raw_bytes = await file.read()
    name_lower = file.filename.lower() if file.filename else ""
    warnings: List[str] = []
    backend: str | None = None
    page_count: int | None = None
    available_backends: List[str] | None = None
    if name_lower.endswith(".pdf"):
        tmp_path = Path("/tmp") / file.filename
        tmp_path.write_bytes(raw_bytes)
        result = extract_pdf_text(tmp_path)
        text = result.text
        backend = result.backend.value
        warnings.extend(result.warnings)
        page_count = len(result.pages)
        available_backends = [b.value for b in detect_available_backends()]
    else:
        text = raw_bytes.decode("utf-8", errors="ignore")
        page_count = None
        available_backends = None
    chapters = simple_chapterize(book_id, text)

    out_dir = Path("data/clean") / book_id
    records: list[dict] = []
    for ch in chapters:
        p = write_chapter_json(ch, out_dir)
        records.append(
            {
                "id": f"{book_id}-{ch.chapter_id}",
                "book_id": book_id,
                "index": ch.index,
                "title": ch.title,
                "text_sha256": ch.text_sha256,
                "json_path": str(p),
                "chapter_id": ch.chapter_id,
            }
        )
    with get_session() as session:
        repository.upsert_book(session, book_id)
        repository.store_chapters(session, records)
    return IngestResponse(
        book_id=book_id,
        chapters=len(records),
        backend=backend,
        warnings=warnings,
        page_count=page_count,
        available_backends=available_backends,
    )


@app.get("/books")
async def list_books() -> list[dict]:
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
            }
            for c in chapters
        ]


@app.get("/chapters/{book_id}/{chapter_id}/annotations")
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
    result = run_annotation_for_chapter(
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
