import httpx
import pytest
from pathlib import Path
import time
import asyncio

from api.app import app
from api.logging_setup import setup_logging
from db import get_session, repository
import shutil
from tests.test_data import REAL_TEST_PDF as REAL_PDF_SRC  # type: ignore

pytestmark = pytest.mark.anyio


def _ensure_pdf(tmp_path: Path, book_id: str, name: str) -> Path:
    bdir = tmp_path / "data" / "books" / book_id / "source_pdfs"
    bdir.mkdir(parents=True, exist_ok=True)
    dest = bdir / name
    if REAL_PDF_SRC.exists():
        shutil.copyfile(REAL_PDF_SRC, dest)
    else:
        dest.write_bytes(b"%PDF-1.4\nMinimal placeholder PDF\n%%EOF")
    return dest


async def test_ingest_job_progress_and_logging(tmp_path: Path, monkeypatch):
    old = Path.cwd()
    monkeypatch.chdir(tmp_path)
    try:
        # Re-init logging so handlers write inside tmp test cwd
        setup_logging(force=True)
        _ensure_pdf(tmp_path, "bkjob", "one.pdf")
        _ensure_pdf(tmp_path, "bkjob", "two.pdf")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            r = await client.post("/ingest_job", data={"book_id": "bkjob"})
            assert r.status_code == 200, r.text
            job_id = r.json()["job_id"]
            # Poll until finished or timeout
            deadline = time.time() + 10
            last = None
            while time.time() < deadline:
                jr = await client.get(f"/jobs/{job_id}")
                assert jr.status_code == 200, jr.text
                data = jr.json()
                last = data
                if data["status"] in {"finished", "error"}:
                    break
                await asyncio.sleep(0.05)
            assert last is not None
            assert last["status"] == "finished"
            params = last["params"]
            # progress metadata
            assert "total_pdfs" in params
            assert params.get("processed_pdfs") == params.get("total_pdfs")
            assert abs(params.get("progress") - 1.0) < 1e-6
            # page-level progress metadata
            assert "total_pages" in params
            assert "processed_pages" in params
            if params.get("total_pages", 0):  # if any pages were detected
                assert params.get("processed_pages") == params.get(
                    "total_pages"
                )
                assert abs(params.get("progress_pages") - 1.0) < 1e-6
        # Verify chapters stored (>= number of pdfs)
        with get_session() as s:
            chs = repository.list_chapters(s, "bkjob")
            assert len(chs) >= 2
        # Check logs exist
        app_log = Path("logs/app.log")
        debug_log = Path("logs/app-debug.log")
        assert app_log.exists(), "app.log missing"
        assert debug_log.exists(), "app-debug.log missing"
        # Basic content check for job start marker
        content = app_log.read_text(encoding="utf-8")
        assert (
            "Job start" in content
            or "Job start"
            in debug_log.read_text(encoding="utf-8")
        )
    finally:
        monkeypatch.chdir(old)
