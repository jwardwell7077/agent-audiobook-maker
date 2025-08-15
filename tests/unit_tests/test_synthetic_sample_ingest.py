import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_synthetic_sample_ingest(tmp_path, monkeypatch):
    # Generate synthetic PDF (intro + 10 chapters)
    out_pdf = Path("data/books/SAMPLE_BOOK/source_pdfs/synthetic_sample.pdf")
    if not out_pdf.exists():
        from scripts.generate_synthetic_sample_pdf import (  # type: ignore
            main as gen_main,
        )
        # Use deterministic seed
        monkeypatch.chdir(Path.cwd())
        import sys
        sys.argv = [
            "gen",
            "--book-id",
            "SAMPLE_BOOK",
            "--chapters",
            "10",
            "--seed",
            "1337",
            "--out",
            str(out_pdf),
        ]
        gen_main()
    resp = client.post(
        "/ingest",
        data={
            "book_id": "SAMPLE_BOOK",
            "pdf_name": "synthetic_sample.pdf",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # We expect 11 emitted records (Intro + 10 chapters)
    assert data["chapters"] == 11
    vpath = data.get("volume_json_path")
    assert vpath
    vol = json.loads(Path(vpath).read_text(encoding="utf-8"))
    assert vol["chapter_count"] == 11
    assert vol["intro_present"] is True
    # Re-ingest (idempotency) -> zero new chapters
    resp2 = client.post(
        "/ingest",
        data={
            "book_id": "SAMPLE_BOOK",
            "pdf_name": "synthetic_sample.pdf",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["chapters"] == 0
