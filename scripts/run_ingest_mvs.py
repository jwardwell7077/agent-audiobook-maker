#!/usr/bin/env python3
"""Run the API app in-process and ingest the canonical SB sample PDF.

Steps:
1. Verify the expected PDF exists at data/books/SB/source_pdfs/real_sample.pdf
2. Start a FastAPI TestClient against the app (no separate server needed)
3. POST /ingest with book_id=SB and pdf_name=real_sample.pdf
4. Print a concise summary (status, chapters, warnings, volume json path)

Usage:
  python scripts/run_ingest_mvs.py

If you prefer hitting a live uvicorn server instead, adapt this to use
httpx.AsyncClient pointing at http://localhost:8000 after starting
`uvicorn api.app:app --reload`.
"""
from __future__ import annotations

import sys
from pathlib import Path
import json
from fastapi.testclient import TestClient

try:
    from api.app import app  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"ERROR: Failed to import app: {e}", file=sys.stderr)
    sys.exit(1)

PDF_PATH = Path("data/books/SB/source_pdfs/real_sample.pdf")
BOOK_ID = "SB"
PDF_NAME = "real_sample.pdf"


def main() -> int:
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found: {PDF_PATH}", file=sys.stderr)
        return 2
    # Detect existing artifacts that would cause continued indexing.
    existing_json = list((Path("data/clean") / BOOK_ID).glob("*.json"))
    if existing_json:
        print(
            f"NOTE: Found {len(existing_json)} existing clean artifacts for "
            f"{BOOK_ID}. Index numbering will continue from current DB "
            "count. For a fresh restart (Intro=0) run: \n  python "
            "scripts/clean_ingest_artifacts.py --db "
            f"{BOOK_ID}"
        )
    client = TestClient(app)
    resp = client.post(
        "/ingest",
        data={
            "book_id": BOOK_ID,
            "pdf_name": PDF_NAME,
            "verbose": 1,
        },
    )
    if resp.status_code != 200:
        print(
            f"Ingest failed ({resp.status_code}): {resp.text}",
            file=sys.stderr,
        )
        return 3
    data = resp.json()
    print("=== Ingest Summary ===")
    print(f"book_id: {data.get('book_id')}")
    print(f"chapters: {data.get('chapters')}")
    print(f"warnings: {data.get('warnings')}")
    vpath = data.get("volume_json_path")
    print(f"volume_json_path: {vpath}")
    if vpath and Path(vpath).exists():
        vol = json.loads(Path(vpath).read_text(encoding='utf-8'))
        print(
            "volume chapter_count: {cc} toc_count: {tc}".format(
                cc=vol.get("chapter_count"), tc=vol.get("toc_count")
            )
        )
    else:
        print("No volume JSON generated (likely structured_toc_parse_failed)")
    return 0

 
if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
