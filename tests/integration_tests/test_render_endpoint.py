import os
# Set DB URL before other imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_render_endpoint.db")

import hashlib
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from db import (  # type: ignore  # pylint: disable=import-error
    get_session,
    models,
)
from api.app import app  # type: ignore  # pylint: disable=import-error

pytestmark = pytest.mark.anyio


async def _ensure_book_chapter(
    book_id: str, chapter_id: str, text: str
) -> None:
    text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chap_pk = f"{book_id}-{chapter_id}"
    with get_session() as session:
        if not session.get(models.Book, book_id):
            session.add(
                models.Book(
                    id=book_id,
                    title="Test Book",
                    author=None,
                )
            )
        if not session.get(models.Chapter, chap_pk):
            session.add(
                models.Chapter(
                    id=chap_pk,
                    book_id=book_id,
                    index=1,
                    title="Chapter 1",
                    text_sha256=text_sha256,
                    payload={"text": text},
                    status="new",
                )
            )


async def test_render_endpoint_force_and_cache(tmp_path: Path) -> None:
    book_id = "bookep"
    chapter_id = "ch1"
    text = "Sentence one. Sentence two."
    await _ensure_book_chapter(book_id, chapter_id, text)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        # Trigger annotation (uncached)
        ann_resp = await client.get(
            f"/chapters/{book_id}/{chapter_id}/annotations",
            params={"force": False, "max_segments": 10},
        )
        assert ann_resp.status_code == 200
        ann = ann_resp.json()
        assert ann["cached"] is False
        segs = ann["segments"]
        assert len(segs) >= 1

        # First render (should synthesize) prefer_xtts false to stay fast
        r1 = await client.post(
            f"/chapters/{book_id}/{chapter_id}/render",
            params={"prefer_xtts": False, "force": False},
        )
        assert r1.status_code == 200
        meta1 = r1.json()
        assert meta1["stem_count"] is not None
        assert Path(meta1["render_path"]).exists()

        # Second render without force should be cached path, stem_count None
        r2 = await client.post(
            f"/chapters/{book_id}/{chapter_id}/render",
            params={"prefer_xtts": False, "force": False},
        )
        assert r2.status_code == 200
        meta2 = r2.json()
        assert meta2["stem_count"] is None  # early-return path
        assert meta2["render_path"] == meta1["render_path"]

        # Force re-render
        before_mtime = Path(meta1["render_path"]).stat().st_mtime
        r3 = await client.post(
            f"/chapters/{book_id}/{chapter_id}/render",
            params={"prefer_xtts": False, "force": True},
        )
        assert r3.status_code == 200
        meta3 = r3.json()
        assert meta3["stem_count"] is not None
        # Re-render should touch file (mtime increases) or create new file path
        after_mtime = Path(meta3["render_path"]).stat().st_mtime
        assert after_mtime >= before_mtime

    # DB assertions (render row exists, gain tracking stored)
    with get_session() as session:
        render = session.get(models.Render, f"{book_id}-{chapter_id}-render")
        assert render is not None
        # applied_gain_db stored in hashes if normalization executed
        if render.hashes:
            assert "applied_gain_db" in render.hashes
