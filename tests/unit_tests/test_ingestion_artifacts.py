import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def _make_pdf(book_id: str, name: str, body: str) -> Path:
    root = Path("data/books") / book_id
    root.mkdir(parents=True, exist_ok=True)
    p = root / name
    p.write_bytes(("%PDF-1.4\n" + body).encode("utf-8"))
    return p


def _structured_sample(chapters: int = 2) -> str:
    toc_lines = [f"Chapter {i}: Title {i}" for i in range(1, chapters + 1)]
    bodies = [
        f"Chapter {i}: Title {i}\nBody {i}." for i in range(1, chapters + 1)
    ]
    return (
        "Intro text here.\nTable of Contents\n"
        + "\n".join(toc_lines)
        + "\n\n"
        + "\n\n".join(bodies)
    )


def test_single_ingest_generates_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book_id = "artifactbook"
    pdf_name = "part1.pdf"
    _make_pdf(book_id, pdf_name, _structured_sample(3))
    resp = client.post(
        "/ingest",
        data={"book_id": book_id, "pdf_name": pdf_name, "verbose": 1},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapters"] >= 1
    # Volume JSON exists
    vpath = Path(data["volume_json_path"])
    assert vpath.exists(), "volume json missing"
    vol = json.loads(vpath.read_text(encoding="utf-8"))
    assert vol["schema_version"] == "1.0"
    assert vol["chapter_count"] == len(vol["chapters"]) == data["chapters"]
    # Chapter JSON artifacts exist for each chapter id referenced
    for ch_entry in vol["chapters"]:
        jp = Path(ch_entry["json_path"]) if ch_entry.get("json_path") else None
        assert jp and jp.exists(), f"chapter json missing: {jp}"
        payload = json.loads(jp.read_text(encoding="utf-8"))
        for k in (
            "book_id",
            "chapter_id",
            "index",
            "title",
            "text",
            "text_sha256",
        ):
            assert k in payload, f"missing field {k} in chapter json"
        assert payload["book_id"] == book_id
    # Ensure volume json has expected suffix
    assert vpath.name.endswith("_volume.json")


def test_batch_ingest_returns_multiple_volume_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book_id = "artifactbatch"
    _make_pdf(book_id, "a.pdf", _structured_sample(1))
    _make_pdf(book_id, "b.pdf", _structured_sample(2))
    resp = client.post("/ingest", data={"book_id": book_id, "verbose": 1})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    paths = data.get("volume_json_paths")
    assert paths and len(paths) == 2
    for vp in paths:
        p = Path(vp)
        assert p.exists(), f"missing volume json {p}"
        meta = json.loads(p.read_text(encoding="utf-8"))
        assert meta["book_id"] == book_id


def test_ingest_failure_creates_no_volume_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    book_id = "artifactfail"
    pdf_name = "fail.pdf"
    # Body lacks TOC & chapter structure -> parser should fail gracefully
    _make_pdf(book_id, pdf_name, "Some random text without structure.")
    resp = client.post(
        "/ingest",
        data={"book_id": book_id, "pdf_name": pdf_name, "verbose": 1},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapters"] == 0
    assert data["volume_json_path"] is None
    # No chapter json files should exist
    ch_dir = Path("data/clean") / book_id
    if ch_dir.exists():
        assert not any(
            ch_dir.glob("*.json")
        ), "Unexpected chapter artifacts on failure"
