import io
from pathlib import Path
import zipfile
import pytest
import httpx

from api.app import app
from db import get_session, repository

pytestmark = pytest.mark.anyio


def _make_zip(pdfs: dict[str, bytes]) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w") as zf:
        for name, content in pdfs.items():
            zf.writestr(name, content)
    return bio.getvalue()


async def test_multi_pdf_ingest_endpoint(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.4\n%%EOF"
    archive = _make_zip({"ch1.pdf": pdf_bytes, "ch2.pdf": pdf_bytes})

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        files = {"file": ("chapters.zip", archive, "application/zip")}
        resp = await client.post(
            "/ingest_multi_pdf", data={"book_id": "mpdemo"}, files=files
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["book_id"] == "mpdemo"
    assert data["chapters"] == 2
    with get_session() as session:
        chapters = repository.list_chapters(session, "mpdemo")
        assert len(chapters) == 2
        for ch in chapters:
            assert "text" in ch.payload
