import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def write_fake_pdf(book_id: str, name: str, body: str) -> Path:
    """Write a pseudo-PDF containing structured TOC style text so that the
    structured_toc parser succeeds during tests. We rely on the raw bytes
    fallback in extraction for these minimal files.
    """
    root = Path("data/books") / book_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    content = "%PDF-1.4\n" + body
    path.write_bytes(content.encode("utf-8"))
    return path


def structured_text(chapter_count: int) -> str:
    # Build a simple intro + TOC + chapter bodies
    toc_lines = [
        f"Chapter {i}: Title {i}" for i in range(1, chapter_count + 1)
    ]
    body_parts = []
    for i in range(1, chapter_count + 1):
        body_parts.append(f"Chapter {i}: Title {i}\nBody {i} text.")
    return (
        "Intro section text here.\nTable of Contents\n"
        + "\n".join(toc_lines)
        + "\n\n"
        + "\n\n".join(body_parts)
    )


def test_ingest_upload_single_pdf(tmp_path, monkeypatch):
    # Isolate workspace
    monkeypatch.chdir(tmp_path)
    book = "uploadbook"
    pdf_bytes = ("%PDF-1.4\n" + structured_text(2)).encode("utf-8")
    files = {"file": ("upload.pdf", pdf_bytes, "application/pdf")}
    resp = client.post(
        "/ingest", data={"book_id": book, "verbose": 1}, files=files
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["book_id"] == book
    # Expect at least 1 parsed chapter (parser may consolidate minimal sample)
    assert data["chapters"] >= 1
    assert data["volume_json_path"], "volume_json_path should be returned"
    vol = json.loads(
        Path(data["volume_json_path"]).read_text(encoding="utf-8")
    )
    assert vol["chapter_count"] >= 1


def test_ingest_batch_mode_with_volume_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book = "batchbook"
    write_fake_pdf(book, "a.pdf", structured_text(1))
    write_fake_pdf(book, "b.pdf", structured_text(2))
    resp = client.post("/ingest", data={"book_id": book, "verbose": 1})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Expect at least one chapter per PDF
    assert data["chapters"] >= 2
    assert data["volume_json_paths"], "volume_json_paths list should exist"
    assert len(data["volume_json_paths"]) == 2


def test_ingest_pdf_name_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book = "storedbook"
    pdf_name = "stored.pdf"
    write_fake_pdf(book, pdf_name, structured_text(3))
    resp = client.post(
        "/ingest", data={"book_id": book, "pdf_name": pdf_name, "verbose": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chapters"] >= 1
    assert data["volume_json_path"].endswith(
        f"{Path(pdf_name).stem}_volume.json"
    )


def test_ingest_both_file_and_pdf_name_prefers_pdf_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book = "conflictbook"
    stored_pdf = "stored.pdf"
    write_fake_pdf(book, stored_pdf, structured_text(3))  # 3 chapters
    # Uploaded file has only 1 chapter to differentiate
    upload_bytes = ("%PDF-1.4\n" + structured_text(1)).encode("utf-8")
    files = {"file": ("upload.pdf", upload_bytes, "application/pdf")}
    resp = client.post(
        "/ingest",
        data={"book_id": book, "pdf_name": stored_pdf, "verbose": 1},
        files=files,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Should reflect stored.pdf selection
    assert data["chapters"] >= 1
    assert data["volume_json_path"].endswith("stored_volume.json")


def test_ingest_nonexistent_pdf_name_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book = "missingbook"
    resp = client.post(
        "/ingest", data={"book_id": book, "pdf_name": "nope.pdf"}
    )
    assert resp.status_code == 404
    assert "pdf_name not found" in resp.text


def test_ingest_verbose_includes_timing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book = "verbbook"
    pdf_name = "v.pdf"
    write_fake_pdf(book, pdf_name, structured_text(2))
    resp = client.post(
        "/ingest", data={"book_id": book, "pdf_name": pdf_name, "verbose": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    # Timing fields should appear when verbose=1
    assert data.get("extraction_ms") is not None
    assert data.get("chapterization_ms") is not None
    # Chunking always false / None currently
    assert data.get("chunking") in (False, None)
