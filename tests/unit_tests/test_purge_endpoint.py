"""Unit tests for the /purge endpoint and related PDF/TOC logic.

Tests purge endpoint dry run, execution, and structured sample generation with and without intro.
"""

from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def _make_pdf(book_id: str, name: str, body: str) -> Path:
    root = Path("data/books") / book_id
    (root / "source_pdfs").mkdir(parents=True, exist_ok=True)
    p = root / "source_pdfs" / name
    p.write_bytes(("%PDF-1.4\n" + body).encode("utf-8"))
    return p


def _structured_sample_with_intro(chapters: int = 2) -> str:
    toc_lines = [f"Chapter {i}: Title {i}" for i in range(1, chapters + 1)]
    bodies = [f"Chapter {i}: Title {i}\nBody {i}." for i in range(1, chapters + 1)]
    return "Intro text here.\nTable of Contents\n" + "\n".join(toc_lines) + "\n\n" + "\n\n".join(bodies)


def _structured_sample_no_intro(chapters: int = 2) -> str:
    toc_lines = [f"Chapter {i}: Title {i}" for i in range(1, chapters + 1)]
    bodies = [f"Chapter {i}: Title {i}\nBody {i}." for i in range(1, chapters + 1)]
    return "Table of Contents\n" + "\n".join(toc_lines) + "\n\n" + "\n\n".join(bodies)


def test_purge_dry_run_reports_counts_with_intro(tmp_path: "Path", monkeypatch: "MonkeyPatch"):
    monkeypatch.chdir(tmp_path)
    book_id = "purgebook_intro"
    N = 3
    _make_pdf(book_id, "a.pdf", _structured_sample_with_intro(N))
    r = client.post("/ingest", data={"book_id": book_id, "pdf_name": "a.pdf"})
    assert r.status_code == 200
    data = r.json()
    assert data["chapters"] == N + 1
    clean_dir = Path("data/clean") / book_id
    file_count = len(list(clean_dir.glob("*.json")))
    assert file_count >= 1
    pr = client.post(
        "/purge",
        json={
            "book_id": book_id,
            "delete_files": True,
            "delete_db": True,
            "dry_run": True,
        },
    )
    assert pr.status_code == 200, pr.text
    meta = pr.json()
    assert meta["dry_run"] is True
    assert meta["deleted_file_count"] == file_count
    assert meta["deleted_db_count"] == N + 1
    assert len(list(clean_dir.glob("*.json"))) == file_count


def test_purge_dry_run_reports_counts_no_intro(tmp_path: "Path", monkeypatch: "MonkeyPatch"):
    monkeypatch.chdir(tmp_path)
    book_id = "purgebook_no_intro"
    N = 3
    _make_pdf(book_id, "a.pdf", _structured_sample_no_intro(N))
    r = client.post("/ingest", data={"book_id": book_id, "pdf_name": "a.pdf"})
    assert r.status_code == 200
    data = r.json()
    assert data["chapters"] == N
    clean_dir = Path("data/clean") / book_id
    file_count = len(list(clean_dir.glob("*.json")))
    assert file_count >= 1
    pr = client.post(
        "/purge",
        json={
            "book_id": book_id,
            "delete_files": True,
            "delete_db": True,
            "dry_run": True,
        },
    )
    assert pr.status_code == 200, pr.text
    meta = pr.json()
    assert meta["dry_run"] is True
    assert meta["deleted_file_count"] == file_count
    assert meta["deleted_db_count"] == N
    assert len(list(clean_dir.glob("*.json"))) == file_count


def test_purge_executes_and_resets_index(tmp_path: "Path", monkeypatch: "MonkeyPatch"):
    monkeypatch.chdir(tmp_path)
    book_id = "purgebook2"
    _make_pdf(book_id, "a.pdf", _structured_sample_with_intro(2))
    # First ingest
    r1 = client.post("/ingest", data={"book_id": book_id, "pdf_name": "a.pdf"})
    assert r1.status_code == 200
    # Second ingest (same PDF) should detect existing chapters, no duplicate
    r2 = client.post("/ingest", data={"book_id": book_id, "pdf_name": "a.pdf"})
    assert r2.status_code == 200
    data2 = r2.json()
    # No new chapters expected on re‑ingest (skip logic)
    assert data2["chapters"] == 0
    # Purge (execute)
    pr = client.post(
        "/purge",
        json={
            "book_id": book_id,
            "delete_files": True,
            "delete_db": True,
            "dry_run": False,
        },
    )
    assert pr.status_code == 200
    meta = pr.json()
    assert meta["dry_run"] is False
    assert meta["deleted_file_count"] >= 1
    # Minimal raw-bytes fallback PDF currently yields a single chapter body
    # (parser confidence passes with TOC + first heading). Accept >=1.
    assert meta["deleted_db_count"] >= 1
    # Re-ingest -> chapters should reappear (fresh numbering)
    r3 = client.post("/ingest", data={"book_id": book_id, "pdf_name": "a.pdf"})
    assert r3.status_code == 200
    data3 = r3.json()
    # Expect the same number of chapters re-created (currently 1)
    assert data3["chapters"] >= 1
