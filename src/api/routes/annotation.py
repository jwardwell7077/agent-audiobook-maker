"""Annotation endpoints for Auto Audiobook Maker API.

This module handles annotation queries and annotation-related helpers.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_session, models
from pipeline.annotation.run import run_annotation_for_chapter

router = APIRouter()


class AnnotationQueryParams(BaseModel):
    """Query parameters for annotation endpoint.

    Attributes:
        force (bool): Force re-annotation.
        enable_coref (bool): Enable coreference resolution.
        enable_emotion (bool): Enable emotion detection.
        enable_qa (bool): Enable QA extraction.
        max_segments (int): Maximum number of segments.
    """

    force: bool = False
    enable_coref: bool = True
    enable_emotion: bool = True
    enable_qa: bool = True
    max_segments: int = 200


def _annotation_qp_dep(
    force: bool = False,
    enable_coref: bool = True,
    enable_emotion: bool = True,
    enable_qa: bool = True,
    max_segments: int = 200,
) -> AnnotationQueryParams:
    """Dependency function to build AnnotationQueryParams from query params.

    Args:
        force (bool): Force re-annotation.
        enable_coref (bool): Enable coreference resolution.
        enable_emotion (bool): Enable emotion detection.
        enable_qa (bool): Enable QA extraction.
        max_segments (int): Maximum number of segments.

    Returns:
        AnnotationQueryParams: Parsed query parameters.
    """
    return AnnotationQueryParams(
        force=force,
        enable_coref=enable_coref,
        enable_emotion=enable_emotion,
        enable_qa=enable_qa,
        max_segments=max_segments,
    )


ANNOTATION_QP_DEP = Depends(_annotation_qp_dep)


@router.get("/chapters/{book_id}/{chapter_id}/annotations")
async def get_chapter_annotations(
    book_id: str,
    chapter_id: str,
    qp: AnnotationQueryParams = ANNOTATION_QP_DEP,
) -> dict[str, Any]:
    """Fetch or compute annotations for a chapter (query params parsed into model).

    Args:
        book_id (str): Book identifier.
        chapter_id (str): Chapter identifier.
        qp (AnnotationQueryParams): Query parameters for annotation.

    Returns:
        dict[str, Any]: Annotation results.

    Raises:
        HTTPException: If chapter is not found.
    """
    with get_session() as session:
        chapter = session.get(models.Chapter, f"{book_id}-{chapter_id}")
        if not chapter:
            raise HTTPException(status_code=404, detail="chapter not found")
    return await run_annotation_for_chapter(
        book_id=book_id,
        chapter_id=chapter_id,
        force=qp.force,
        enable_coref=qp.enable_coref,
        enable_emotion=qp.enable_emotion,
        enable_qa=qp.enable_qa,
        max_segments=qp.max_segments,
    )
