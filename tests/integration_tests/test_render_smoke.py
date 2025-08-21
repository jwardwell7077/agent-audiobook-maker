from pathlib import Path

import pytest

from agent import State, graph
from db import get_session, models  # type: ignore  # noqa: E501  # pylint: disable=import-error
from tts.engines import synthesize_and_render_chapter  # updated import

pytestmark = pytest.mark.anyio


async def test_render_smoke(tmp_path: Path) -> None:
    # Build a tiny annotated set of segments via graph
    text = "Hello world. Another test sentence."  # two segments expected
    state = State(text=text, max_segments=5)
    result = await graph.ainvoke(state)
    segments = result["segments"]

    # Synthesize using stub fallback only (avoid heavy XTTS load in test)
    data_root = tmp_path / "data"
    meta = synthesize_and_render_chapter(
        book_id="book1",
        chapter_id="ch1",
        segments=segments,
        data_root=data_root,
        prefer_xtts=False,
    )

    # Filesystem assertions
    render_path = Path(meta["render_path"])
    assert render_path.exists(), "Render file should exist"
    stems_dir = data_root / "stems" / "book1" / "ch1"
    stem_files = list(stems_dir.glob("*.wav"))
    assert len(stem_files) == len(segments)

    # Basic metadata assertions
    assert meta["stem_count"] == len(segments)
    assert meta["duration_s"] is not None
    assert meta["peak_dbfs"] is not None

    # DB row assertions
    with get_session() as session:
        render_id = "book1-ch1-render"
        render = session.get(models.Render, render_id)
        assert render is not None
        assert render.path == str(render_path)
        stems = session.query(models.Stem).filter_by(book_id="book1").all()
        assert len(stems) == len(segments)

    # Re-run to ensure idempotent updates not duplications
    meta2 = synthesize_and_render_chapter(
        book_id="book1",
        chapter_id="ch1",
        segments=segments,
        data_root=data_root,
        prefer_xtts=False,
    )
    assert meta2["stem_count"] == meta["stem_count"]
    # stems count in DB still same
    with get_session() as session:
        stems = session.query(models.Stem).filter_by(book_id="book1").all()
        assert len(stems) == len(segments)
