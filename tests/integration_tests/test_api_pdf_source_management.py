from pathlib import Path

import httpx
import pytest

from api.app import app
from db import get_session, repository

pytestmark = pytest.mark.anyio


def _pdf_bytes() -> bytes:
    """Return minimal PDF bytes; body not parsed in these tests."""
    return b"%PDF-1.4\n%%EOF"


aSYNC_TIMEOUT = 30


async def test_upload_and_list_pdfs(tmp_path: Path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = [
            ("files", ("part1.pdf", _pdf_bytes(), "application/pdf")),
            ("files", ("part2.pdf", _pdf_bytes(), "application/pdf")),
        ]
        resp = await client.post("/books/demo_book/pdfs", files=files)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["book_id"] == "demo_book"
        assert set(data["saved"]) == {"part1.pdf", "part2.pdf"}

        list_resp = await client.get("/books/demo_book/pdfs")
        assert list_resp.status_code == 200
        lst = list_resp.json()
        assert lst["book_id"] == "demo_book"
        names = {p["name"] for p in lst["pdfs"]}
        assert names == {"part1.pdf", "part2.pdf"}

        ingest_resp = await client.post("/books/demo_book/ingest_pdfs")
        assert ingest_resp.status_code == 200, ingest_resp.text
        ingest_data = ingest_resp.json()
        assert ingest_data["book_id"] == "demo_book"
        assert ingest_data["chapters"] == 2
        assert set(ingest_data["pdfs"]) == {"part1.pdf", "part2.pdf"}

    # Verify chapters persisted
    with get_session() as session:
        chapters = repository.list_chapters(session, "demo_book")
        assert len(chapters) == 2
        for ch in chapters:
            assert ch.payload.get("source_pdf")
            assert ch.payload.get("json_path")
