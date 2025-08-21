"""Dagster asset definitions (demo ingestion, annotation, render)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dagster import AssetExecutionContext, asset

from db import get_session, models, repository
from pipeline.annotation.run import run_annotation_for_chapter
from pipeline.casting.derive import derive_characters, persist_characters
from pipeline.ingestion.chapterizer import simple_chapterize, write_chapter_json
from pipeline.ssml.build import build_ssml
from tts.engines import synthesize_and_render_chapter  # updated path

DATA_ROOT = Path("data")


@asset(group_name="ingestion")
def chapters_clean(
    context: AssetExecutionContext,
) -> list[str]:  # pragma: no cover
    """Produce demo chapters from README.md and persist them.

    Serves as a placeholder ingestion asset for Dagster examples.
    """
    book_id = "demo"
    source = Path("README.md").read_text(encoding="utf-8")
    chapters = simple_chapterize(book_id, source)
    out_dir = DATA_ROOT / "clean" / book_id
    records: list[dict[str, Any]] = []
    paths: list[str] = []
    for ch in chapters:
        p = write_chapter_json(ch, out_dir)
        paths.append(str(p))
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
    context.log.info(json.dumps({"count": len(paths)}))
    return paths


@asset(group_name="annotation", deps=[chapters_clean])
async def chapter_annotations(
    context: AssetExecutionContext,
) -> None:  # pragma: no cover
    """Compute annotations for all clean chapters if missing.

    Future: convert to partitioned asset (book_id, chapter_id).
    """
    annotated = 0
    with get_session() as session:
        books = repository.list_books(session)
        for b in books:
            chapters = repository.list_chapters(session, b.id)
            for ch in chapters:
                chap_id = ch.id.split("-", 1)[1]
                try:
                    res = await run_annotation_for_chapter(
                        book_id=b.id,
                        chapter_id=chap_id,
                    )
                    if not res.get("cached"):
                        annotated += 1
                except Exception as e:  # noqa: BLE001
                    context.log.warning(
                        f"annotation_failed book={b.id} chapter={chap_id} error={e}"  # noqa: E501
                    )
    context.log.info(f"annotation completed newly_computed={annotated}")


@asset(group_name="render", deps=[chapter_annotations])
def chapter_renders(
    context: AssetExecutionContext,
) -> None:  # pragma: no cover
    """Derive characters, build SSML, synthesize stems, mix chapter audio.

    Uses XTTS v2 if available else Piper stub; persists stems and render rows.
    """
    with get_session() as session:
        books = repository.list_books(session)
        for b in books:
            chapters = repository.list_chapters(session, b.id)
            for ch in chapters:
                chap_id = ch.id.split("-", 1)[1]
                ann_id = f"{ch.id}-v1"
                ann = session.get(models.Annotation, ann_id)
                if not ann or ann.status != "succeeded":
                    continue
                segments = ann.records
                chars = derive_characters(b.id, segments)
                persist_characters(chars)
                voice_map = {c.name: c.name for c in chars}
                ssml = build_ssml(segments, voice_map)
                ssml_dir = DATA_ROOT / "ssml" / b.id
                ssml_dir.mkdir(parents=True, exist_ok=True)
                (ssml_dir / f"{chap_id}.ssml").write_text(
                    ssml,
                    encoding="utf-8",
                )
                meta = synthesize_and_render_chapter(
                    b.id,
                    chap_id,
                    segments,
                    data_root=DATA_ROOT,
                    prefer_xtts=True,
                )
                context.log.info(
                    f"render_complete book={b.id} chapter={chap_id} duration_s={meta.get('duration_s')} stems={meta.get('stem_count')}"  # noqa: E501
                )
    context.log.info("chapter_renders complete")
