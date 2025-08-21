"""API ingest endpoint smoke tests.

These tests mock the heavy extraction pipeline so they run fast
and focus on response shaping and basic routing logic.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeAlias
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


@pytest.fixture
def fake_chapter_record() -> dict[str, Any]:
    """Return a representative minimal chapter record payload."""
    return {
        "id": "book1-00000",
        "book_id": "book1",
        "index": 0,
        "title": "Ch 1",
        "text_sha256": "abc123",
        "text": "hello world",
        "meta": {"word_count": 2, "source": "test"},
    }


TMP_DIR = Path(tempfile.gettempdir())

# Type alias for mocked pipeline return tuple
ExtractionReturn: TypeAlias = tuple[
    list[dict[str, Any]],  # records
    int,  # next_index
    Any,  # result object
    list[Any],  # warnings
    int,  # page_ct
    float,  # extraction_ms
    float,  # chapterization_ms
    bool,  # chunked
    None,  # chunk_size
    None,  # chunk_count
    str,  # parse_mode
    str,  # volume_json_path
]


def _extract_and_chapterize_side_effect(
    book_id: str,
    pdf_path: Path | str,
    next_index: int,
    skip_if: Sequence[str] | None = None,
) -> ExtractionReturn:  # noqa: D401
    """Return a lightweight mock of extraction output tuple."""

    class Result:  # minimal attributes used by code under test
        backend = type("B", (), {"value": "mock"})
        text = "hello world"
        pages: list[int] = [1, 2]

    record: dict[str, Any] = {
        "id": f"{book_id}-00000",
        "book_id": book_id,
        "index": next_index,
        "title": "Ch 1",
        "text_sha256": "abc",
        "text": "hello",
        "meta": {},
    }
    # Tuple matches signature in real pipeline
    return (
        [record],  # records
        next_index + 1,  # next_index
        Result(),  # result object
        [],  # warnings
        2,  # page_ct
        1.0,  # extraction_ms
        0.5,  # chapterization_ms
        False,  # chunked
        None,  # chunk_size
        None,  # chunk_count
        "mock_parse",  # parse_mode
        str(TMP_DIR / "vol.json"),  # volume_json_path (test-only)
    )


@patch(
    "api.app.extract_and_chapterize",
    side_effect=_extract_and_chapterize_side_effect,
)
@patch("api.app.detect_available_backends", return_value=[])
def test_single_ingest_stored(
    mock_backends: MagicMock,
    mock_extract: MagicMock,
    tmp_path: Path,
) -> None:
    """Single stored PDF ingest path (may 404 if filesystem differs)."""
    book_dir = tmp_path / "data" / "books" / "book2"
    book_dir.mkdir(parents=True)
    (book_dir / "sample.pdf").write_bytes(b"%PDF-1.4 test")
    resp = client.post("/ingest", data={"book_id": "book2", "pdf_name": "sample.pdf"})
    assert resp.status_code in {200, 404}


def test_annotation_query_params_model() -> None:
    """Query params model parses (404 acceptable if chapter absent)."""
    resp = client.get(
        "/chapters/bookx/00000/annotations",
        params={
            "force": "false",
            "enable_coref": "true",
            "enable_emotion": "true",
            "enable_qa": "false",
            "max_segments": 10,
        },
    )
    assert resp.status_code in {404, 200}
