import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)

BOOK_ID = "SB"
PDF_NAME = "real_sample.pdf"

EXPECTED_DIR = Path("tests/test_data/mvs_expected")


def test_mvs_canonical_volume_and_intro(monkeypatch, tmp_path):
    # Copy real sample PDF fixture from repo into tmp test dir if present
    source_pdf = Path("data/books/SB/source_pdfs") / PDF_NAME
    if not source_pdf.exists():  # skip if canonical pdf missing
        import pytest
        pytest.skip("canonical SB pdf missing from repo")
    # run in repo root (assumes canonical paths)
    # ingest
    resp = client.post(
        "/ingest", data={"book_id": BOOK_ID, "pdf_name": PDF_NAME}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    vpath = Path(data["volume_json_path"])
    assert vpath.exists(), "volume json missing"
    vol = json.loads(vpath.read_text(encoding="utf-8"))
    expected_vol = json.loads(
        (EXPECTED_DIR / "real_sample_volume.json").read_text(encoding="utf-8")
    )
    # Stable structural assertions (avoid timing fields)
    for k in (
        "book_id",
        "pdf_name",
        "chapter_count",
        "toc_count",
        "heading_count",
        "intro_present",
    ):
        assert vol.get(k) == expected_vol.get(k)
    assert vol["toc"][0]["title"] == expected_vol["toc_first_sha"]
    assert vol["toc"][-1]["title"] == expected_vol["toc_last_sha"]
    # Intro chapter hash
    intro_path = Path("data/clean") / BOOK_ID / "00000.json"
    assert intro_path.exists(), "intro chapter missing"
    intro = json.loads(intro_path.read_text(encoding="utf-8"))
    expected_intro = json.loads(
        (EXPECTED_DIR / "00000.json").read_text(encoding="utf-8")
    )
    for k in ("book_id", "chapter_id", "index", "title", "text_sha256"):
        assert intro.get(k) == expected_intro.get(k)


def test_mvs_purge_regression(monkeypatch, tmp_path):
    source_pdf = Path("data/books/SB/source_pdfs") / PDF_NAME
    if not source_pdf.exists():  # skip if canonical pdf missing
        import pytest
        pytest.skip("canonical SB pdf missing from repo")
    # First ingest to populate artifacts
    r1 = client.post(
        "/ingest", data={"book_id": BOOK_ID, "pdf_name": PDF_NAME}
    )
    assert r1.status_code == 200
    # Collect hashes snapshot
    hashes_path = Path("tests/test_data/mvs_expected/chapters_sha256.json")
    expected_hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
    # Purge artifacts + DB
    pr = client.post(
        "/purge",
        json={
            "book_id": BOOK_ID,
            "delete_files": True,
            "delete_db": True,
            "dry_run": False,
        },
    )
    assert pr.status_code == 200, pr.text
    meta = pr.json()
    assert meta["deleted_file_count"] >= 1
    assert meta["deleted_db_count"] >= 1
    # Re-ingest after purge
    r2 = client.post(
        "/ingest", data={"book_id": BOOK_ID, "pdf_name": PDF_NAME}
    )
    assert r2.status_code == 200
    # Verify hashes match expected canonical snapshot
    for ch_id, expected_hash in expected_hashes.items():
        p = Path("data/clean") / BOOK_ID / f"{ch_id}.json"
        assert p.exists(), (
            f"chapter json missing after purge reingest: {ch_id}"
        )
        payload = json.loads(p.read_text(encoding="utf-8"))
        got = payload.get("text_sha256")
        if got != expected_hash:
            # Helper: show first differing line via unified diff
            # We don't have stored canonical text, so emit first lines as aid
            full_text = payload.get("text", "")
            lines = full_text.splitlines()
            preview = "\\n".join(lines[:20])
            raise AssertionError(
                "hash mismatch {cid} expected={exp} got={got}\n".format(
                    cid=ch_id, exp=expected_hash, got=got
                ) + "text preview:\n" + preview
            )
        assert got == expected_hash
