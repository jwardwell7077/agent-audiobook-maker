#!/usr/bin/env python3
"""Run the API app in-process and ingest a canonical SAMPLE_BOOK demo PDF.

Steps:
1. Verify PDF exists at data/books/SAMPLE_BOOK/source_pdfs/sample.pdf
2. Start a FastAPI TestClient against the app (no separate server needed)
3. POST /ingest with book_id=SAMPLE_BOOK and pdf_name=sample.pdf
4. Print a concise summary (status, chapters, warnings, volume json path)

Usage:
  python scripts/run_ingest_sample.py

If you prefer hitting a live uvicorn server instead, adapt this to use
httpx.AsyncClient pointing at http://localhost:8000 after starting
`uvicorn api.app:app --reload`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

try:
    from api.app import app  # type: ignore
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"ERROR: Failed to import app: {e}\n")
    sys.exit(1)

HTTP_OK = 200


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a demo/sample PDF via in-process FastAPI client")
    parser.add_argument("--book-id", default="SAMPLE_BOOK", help="Book identifier (default: SAMPLE_BOOK)")
    parser.add_argument(
        "--pdf-name",
        default="sample.pdf",
        help="PDF filename under data/books/<book-id>/source_pdfs (default: sample.pdf)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Ingest the sample PDF via in-process FastAPI client and summarize."""
    ns = _parse_args(argv)
    book_id: str = ns.book_id
    pdf_name: str = ns.pdf_name
    pdf_path = Path("data/books") / book_id / "source_pdfs" / pdf_name
    if not pdf_path.exists():
        sys.stderr.write(f"ERROR: PDF not found: {pdf_path}\n")
        return 2
    existing_json = list((Path("data/clean") / book_id).glob("*.json"))
    if existing_json:
        sys.stdout.write("NOTE: Found ")
        sys.stdout.write(f"{len(existing_json)} existing artifacts for {book_id}. ")
        sys.stdout.write("Index numbering will continue from current DB count. ")
        sys.stdout.write("For a fresh restart (Intro=0) run: \n  python ")
        sys.stdout.write("scripts/clean_ingest_artifacts.py --db ")
        sys.stdout.write(f"{book_id}\n")
    client = TestClient(app)
    resp = client.post(
        "/ingest",
        data={
            "book_id": book_id,
            "pdf_name": pdf_name,
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
