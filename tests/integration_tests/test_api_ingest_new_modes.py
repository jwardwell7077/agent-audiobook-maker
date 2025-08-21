"""Integration tests for new ingest modes in the API.

Tests single and batch ingest endpoints, ensuring idempotency and correct DB state.
"""

import shutil
from pathlib import Path
from pathlib import Path as _P

import httpx
import pytest

from api.app import app
from db import get_session, repository

REAL_PDF_SRC = _P(__file__).resolve().parent.parent / "test_data" / "real_sample.pdf"

pytestmark = pytest.mark.anyio


def _ensure_pdf(tmp_path: Path, book_id: str, name: str) -> Path:
    """Ensure a PDF file exists for testing, copying a real or placeholder file.

    Args:
        tmp_path (Path): Temporary directory for test files.
        book_id (str): Book identifier.
        name (str): PDF filename.

    Returns:
        Path: Path to the ensured PDF file.
    """
    bdir = tmp_path / "data" / "books" / book_id / "source_pdfs"
    bdir.mkdir(parents=True, exist_ok=True)
    dest = bdir / name
    if REAL_PDF_SRC.exists():
        shutil.copyfile(REAL_PDF_SRC, dest)
    else:
        dest.write_bytes(b"%PDF-1.4\nMinimal placeholder PDF\n%%EOF")
    return dest


async def test_ingest_single_stored_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ingesting a single stored PDF and verify idempotency and DB state.

    Args:
        tmp_path (Path): Temporary directory for test files.
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
    """
    # isolate cwd
    old = Path.cwd()
    monkeypatch.chdir(tmp_path)
    try:
        _ensure_pdf(tmp_path, "bk1", "chunks1.pdf")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Ingest single stored pdf
            r = await client.post("/ingest", data={"book_id": "bk1", "pdf_name": "chunks1.pdf"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["book_id"] == "bk1"
            assert data["chapters"] >= 1
            # Idempotent second call should not duplicate because title matches
            r2 = await client.post("/ingest", data={"book_id": "bk1", "pdf_name": "chunks1.pdf"})
            assert r2.status_code == 200
            # Chapters count in DB should remain same
            with get_session() as s:
                chs = repository.list_chapters(s, "bk1")
                assert len(chs) == data["chapters"]
    finally:
        monkeypatch.chdir(old)


async def test_ingest_batch_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test batch ingest mode and verify chapters are not duplicated.

    Args:
        tmp_path (Path): Temporary directory for test files.
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
    """
    old = Path.cwd()
    monkeypatch.chdir(tmp_path)
    try:
        _ensure_pdf(tmp_path, "bk2", "partA.pdf")
        _ensure_pdf(tmp_path, "bk2", "partB.pdf")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/ingest", data={"book_id": "bk2"})
            assert r.status_code == 200, r.text
            data = r.json()
            # Expect at least one chapter per PDF
            assert data["chapters"] >= 2
            # Re-run batch should skip duplicates (no growth)
            r2 = await client.post("/ingest", data={"book_id": "bk2"})
            assert r2.status_code == 200
            with get_session() as s:
                chs = repository.list_chapters(s, "bk2")
                assert len(chs) == data["chapters"]
    finally:
        monkeypatch.chdir(old)
