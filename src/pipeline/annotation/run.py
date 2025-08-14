from __future__ import annotations

"""Annotation execution & persistence utilities.

Provides a synchronous helper to run the LangGraph annotation pipeline for a
single chapter and persist outputs to filesystem (JSONL) and database.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Dict, Any
import json
import hashlib
import time

from agent import graph, State, Segment
from db import get_session, models

ANNOTATION_DIR = Path("data/annotations")
GRAPH_VERSION = 1  # bump if node semantics change


def _hash_params(params: Dict[str, Any]) -> str:
    # Deterministic hash of sorted items + graph version
    items = sorted(params.items()) + [("graph_version", GRAPH_VERSION)]
    m = hashlib.sha256()
    for k, v in items:
        m.update(str(k).encode())
        m.update(b"=")
        m.update(str(v).encode())
        m.update(b";")
    return m.hexdigest()


async def run_annotation_for_chapter(
    book_id: str,
    chapter_id: str,
    force: bool = False,
    enable_coref: bool = True,
    enable_emotion: bool = True,
    enable_qa: bool = True,
    max_segments: int = 200,
) -> Dict[str, Any]:
    """Run annotation graph for a stored chapter, with caching.

    Returns dict: status, chapter_id, book_id, segments, cached.
    """
    chap_pk = f"{book_id}-{chapter_id}"
    with get_session() as session:
        chapter = session.get(models.Chapter, chap_pk)
        if not chapter:
            raise ValueError("Chapter not found")
        text_sha256 = chapter.text_sha256
        params = {
            "enable_coref": enable_coref,
            "enable_emotion": enable_emotion,
            "enable_qa": enable_qa,
            "max_segments": max_segments,
        }
        params_hash = _hash_params(params)

        # Check existing annotation
        ann_id = f"{chap_pk}-v{GRAPH_VERSION}"
        existing = session.get(models.Annotation, ann_id)
        if (
            existing
            and existing.text_sha256 == text_sha256
            and existing.params_sha256 == params_hash
            and existing.status == "succeeded"
            and not force
        ):
            return {
                "status": "ok",
                "cached": True,
                "book_id": book_id,
                "chapter_id": chapter_id,
                "segments": existing.records,
            }
        # Load chapter JSON text from file
        ch_payload = chapter.payload
        raw_text = (
            ch_payload.get("text")
            if isinstance(ch_payload, dict)
            else None
        )
        if not raw_text:
            raise ValueError("Chapter payload missing text")

        state = State(
            text=raw_text,
            enable_coref=enable_coref,
            enable_emotion=enable_emotion,
            enable_qa=enable_qa,
            max_segments=max_segments,
        )

        start = time.time()
        try:
            # Use async invocation (nodes may be async)
            result = await graph.ainvoke(state)
            segments: Iterable[Segment] = result["segments"]
            elapsed = time.time() - start
            records: List[Dict[str, Any]] = []
            for i, seg in enumerate(segments):
                d = asdict(seg)
                d.update(
                    {
                        "book_id": book_id,
                        "chapter_id": chapter_id,
                        "utterance_idx": i,
                    }
                )
                records.append(d)
            stats = {
                "segment_count": len(records),
                "elapsed_s": elapsed,
            }
            # Persist JSONL
            out_dir = ANNOTATION_DIR / book_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{chapter_id}.jsonl"
            with out_path.open("w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            # Upsert annotation row
            if not existing:
                existing = models.Annotation(
                    id=ann_id,
                    book_id=book_id,
                    chapter_id=chap_pk,
                    version=GRAPH_VERSION,
                    records=records,
                    stats=stats,
                    text_sha256=text_sha256,
                    params_sha256=params_hash,
                    status="succeeded",
                )
                session.add(existing)
            else:
                existing.records = records
                existing.stats = stats
                existing.text_sha256 = text_sha256
                existing.params_sha256 = params_hash
                existing.status = "succeeded"
            return {
                "status": "ok",
                "cached": False,
                "book_id": book_id,
                "chapter_id": chapter_id,
                "segments": records,
            }
        except Exception as e:  # noqa: BLE001
            if existing:
                existing.status = "failed"
            else:
                session.add(
                    models.Annotation(
                        id=ann_id,
                        book_id=book_id,
                        chapter_id=chap_pk,
                        version=GRAPH_VERSION,
                        records=[],
                        stats={"error": str(e)},
                        text_sha256=text_sha256,
                        params_sha256=params_hash,
                        status="failed",
                    )
                )
            raise


__all__ = ["run_annotation_for_chapter", "_hash_params"]
