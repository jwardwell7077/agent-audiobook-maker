#!/usr/bin/env python3
"""Run the API app in-process and ingest the canonical MVS sample PDF.

Steps:
1. Verify the expected PDF exists at data/books/MVS/source_pdfs/real_sample.pdf
2. Start a FastAPI TestClient against the app (no separate server needed)
3. POST /ingest with book_id=MVS and pdf_name=real_sample.pdf
4. Print a concise summary (status, chapters, warnings, volume json path)

Usage:
  python scripts/run_ingest_mvs.py

If you prefer hitting a live uvicorn server instead, adapt this to use
httpx.AsyncClient pointing at http://localhost:8000 after starting
`uvicorn api.app:app --reload`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

try:
    from api.app import app  # type: ignore
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"ERROR: Failed to import app: {e}\n")
    sys.exit(1)

PDF_PATH = Path("data/books/MVS/source_pdfs/real_sample.pdf")
BOOK_ID = "MVS"
PDF_NAME = "real_sample.pdf"
HTTP_OK = 200


def main() -> int:
    """Ingest MVS sample PDF via in-process FastAPI client and summarize."""
    if not PDF_PATH.exists():
        sys.stderr.write(f"ERROR: PDF not found: {PDF_PATH}\n")
        return 2
    # Detect existing artifacts that would cause continued indexing.
    existing_json = list((Path("data/clean") / BOOK_ID).glob("*.json"))
    if existing_json:
        sys.stdout.write(f"NOTE: Found {len(existing_json)} existing clean artifacts for {BOOK_ID}.\n")
    client = TestClient(app)
    resp = client.post(
        "/ingest",
        data={
            "book_id": BOOK_ID,
            "pdf_name": PDF_NAME,
            "verbose": 1,
        },
    )
    if resp.status_code != HTTP_OK:
        sys.stderr.write(f"Ingest failed ({resp.status_code}): {resp.text}\n")
        return 3
    data = resp.json()
    sys.stdout.write("=== Ingest Summary ===\n")
    sys.stdout.write(f"book_id: {data.get('book_id')}\n")
    sys.stdout.write(f"chapters: {data.get('chapters')}\n")
    sys.stdout.write(f"warnings: {data.get('warnings')}\n")
    vpath = data.get("volume_json_path")
    sys.stdout.write(f"volume_json_path: {vpath}\n")
    if vpath and Path(vpath).exists():
        vol = json.loads(Path(vpath).read_text(encoding="utf-8"))
        sys.stdout.write(
            "volume chapter_count: {cc} toc_count: {tc}\n".format(cc=vol.get("chapter_count"), tc=vol.get("toc_count"))
        )
    else:
        sys.stdout.write("No volume JSON generated (likely structured_toc_parse_failed)\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
