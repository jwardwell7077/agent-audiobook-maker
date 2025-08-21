"""Rendering endpoints for Auto Audiobook Maker API.

This module handles chapter rendering and related helpers.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from db import get_session, models
from pipeline.annotation.run import run_annotation_for_chapter
from tts.engines import synthesize_and_render_chapter

router = APIRouter()


@router.post("/chapters/{book_id}/{chapter_id}/render")
async def render_chapter(
    book_id: str,
    chapter_id: str,
    force: bool = False,
    prefer_xtts: bool = True,
) -> dict[str, Any]:
    """Trigger (or fetch existing) chapter render.

    If a render row already exists and force is False, returns its metadata
    without recomputing. Otherwise synthesizes stems and stitches.

    Args:
        book_id (str): Book identifier.
        chapter_id (str): Chapter identifier.
        force (bool): Force re-rendering if True.
        prefer_xtts (bool): Prefer XTTS engine if True.

    Returns:
        dict[str, Any]: Render metadata.

    Raises:
        HTTPException: If chapter is not found.
    """
    with get_session() as session:
        chapter_key = f"{book_id}-{chapter_id}"
        chapter = session.get(models.Chapter, chapter_key)
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")
        render_id = f"{book_id}-{chapter_id}-render"
        existing = session.get(models.Render, render_id)
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
    ann = await run_annotation_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        force=force,
        enable_coref=True,
        enable_emotion=True,
        enable_qa=True,
        max_segments=200,
    )
    segments = ann.get("segments", [])
    meta = synthesize_and_render_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        segments=segments,
        prefer_xtts=prefer_xtts,
    )
    return meta
