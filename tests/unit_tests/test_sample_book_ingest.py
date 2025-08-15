import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)

BOOK_ID = "SAMPLE_BOOK"
PDF_NAME = "sample.pdf"

EXPECTED_DIR = Path("tests/test_data/sample_expected")


def test_sample_book_ingest_smoke(tmp_path):
    source_pdf = Path("data/books/SAMPLE_BOOK/source_pdfs") / PDF_NAME
    if not source_pdf.exists():  # skip if demo pdf missing
        import pytest
        pytest.skip("demo SAMPLE_BOOK pdf missing from repo")
    resp = client.post(
        "/ingest", data={"book_id": BOOK_ID, "pdf_name": PDF_NAME}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    vpath = Path(data["volume_json_path"])
    assert vpath.exists(), "volume json missing"
    vol = json.loads(vpath.read_text(encoding="utf-8"))
    # Minimal structural assertions (avoid text hashes since sample text
    # may change)
    for k in ("book_id", "pdf_name", "chapter_count", "toc_count"):
        assert k in vol
    assert vol.get("book_id") == BOOK_ID
