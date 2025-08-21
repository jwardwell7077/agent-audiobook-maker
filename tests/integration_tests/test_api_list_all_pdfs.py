"""Integration tests for listing PDFs across all books.

These tests exercise upload endpoints and the aggregate `/pdfs` listing to ensure
the response groups PDFs by book id and returns expected relative names.
"""

import os
from pathlib import Path

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch

from api.app import app

pytestmark = pytest.mark.anyio


def _pdf_bytes() -> bytes:
    """Return minimal well-formed PDF header/footer bytes for uploads."""
    return b"%PDF-1.4\n%%EOF"


async def test_list_all_pdfs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Upload multiple PDFs across books then assert aggregate listing structure."""
    # Point data/books to isolated tmp directory to avoid pollution
    custom_root = tmp_path / "data" / "books"
    custom_root.mkdir(parents=True, exist_ok=True)
    # Monkeypatch Path used inside endpoint by temporarily chdir
    old_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Initially empty
            resp_empty = await client.get("/pdfs")
            assert resp_empty.status_code == 200
            assert resp_empty.json() == {"books": []}

            # Upload PDFs for two books
            files_a = [
                ("files", ("a1.pdf", _pdf_bytes(), "application/pdf")),
                ("files", ("a2.pdf", _pdf_bytes(), "application/pdf")),
            ]
            files_b = [
                ("files", ("b1.pdf", _pdf_bytes(), "application/pdf")),
            ]
            r1 = await client.post("/books/bookA/pdfs", files=files_a)
            assert r1.status_code == 200, r1.text
            r2 = await client.post("/books/bookB/pdfs", files=files_b)
            assert r2.status_code == 200, r2.text

            # List all again
            resp_all = await client.get("/pdfs")
            data = resp_all.json()
            assert resp_all.status_code == 200
            # Convert to mapping for easier assertions
            mapping = {b["book_id"]: b["pdfs"] for b in data["books"]}
            assert set(mapping.keys()) == {"bookA", "bookB"}
            assert {p["name"] for p in mapping["bookA"]} == {
                "source_pdfs/a1.pdf",
                "source_pdfs/a2.pdf",
            }
            assert {p["name"] for p in mapping["bookB"]} == {"source_pdfs/b1.pdf"}
    finally:
        os.chdir(old_cwd)
