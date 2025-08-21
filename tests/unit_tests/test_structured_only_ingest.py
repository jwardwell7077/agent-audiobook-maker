"""Integration-ish tests for structured TOC ingestion endpoint.

Covers success (chapters produced) and failure (zero chapters) paths.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from api.app import app

client = TestClient(app)


def write_temp_pdf(book_id: str, name: str, text: str) -> Path:
    """Create a pseudo PDF file containing plain text for ingestion tests."""
    # Minimal PDF header so extraction path attempts then falls back.
    root = Path("data/books") / book_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_bytes(b"%PDF-1.4\n" + text.encode("utf-8"))
    return path


def test_structured_parse_success(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Ingest a pseudo PDF with valid structured TOC expecting chapters."""
    book = "testbook1"
    pdf_name = "sample.pdf"
    sample_text = (
        "Intro stuff here\nTable of Contents\n"
        "Chapter 1: One\nChapter 2: Two\n\n"
        "Chapter 1: One\nBody one.\n\nChapter 2: Two\nBody two."
    )
    write_temp_pdf(book, pdf_name, sample_text)
    resp = client.post(
        "/ingest",
        data={
            "book_id": book,
            "pdf_name": pdf_name,
            "verbose": 1,
        },  # type: ignore[arg-type]
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapters"] >= 2
    assert data["parse_mode"] == "structured_toc"
    assert data["volume_json_path"]
    vol = json.loads(Path(data["volume_json_path"]).read_text(encoding="utf-8"))
    assert vol["chapter_count"] >= 2
    assert vol["schema_version"] == "1.0"


def test_structured_parse_failure(tmp_path: Path) -> None:
    """Ingest pseudo PDF lacking structure expecting zero chapters."""
    book = "testbook2"
    pdf_name = "sample2.pdf"
    sample_text = "Just some text without chapters or toc."
    write_temp_pdf(book, pdf_name, sample_text)
    resp = client.post(
        "/ingest",
        data={
            "book_id": book,
            "pdf_name": pdf_name,
            "verbose": 1,
        },  # type: ignore[arg-type]
    )
    assert resp.status_code == 200
    data = resp.json()
    # Expect zero chapters because parser should fail and return empty list
    assert data["chapters"] == 0
    assert data["parse_mode"] == "structured_toc"
    # volume_json_path should be null because no chapters written
    assert data["volume_json_path"] is None
