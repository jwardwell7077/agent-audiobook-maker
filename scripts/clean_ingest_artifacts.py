#!/usr/bin/env python3
"""Clean ingestion artifacts for a given book (default: SAMPLE_BOOK).

Removes generated chapter and volume JSON files under data/clean/<book_id>
so you can perform a fresh ingestion run without stale artifacts.

Usage:
    python scripts/clean_ingest_artifacts.py  # clean SAMPLE_BOOK (files)
    python scripts/clean_ingest_artifacts.py BOOK_ID  # clean specific book
    python scripts/clean_ingest_artifacts.py --all  # clean all books
    python scripts/clean_ingest_artifacts.py --db SAMPLE_BOOK  # purge DB rows

Safety: only touches data/clean; never deletes source_pdfs or DB files.
Use --dry-run to preview deletions.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

try:  # optional DB ops; skip if DB not initialised
    from db import get_session  # type: ignore
    from db import repository  # type: ignore
except Exception:  # noqa: BLE001
    get_session = None  # type: ignore
    repository = None  # type: ignore

CLEAN_ROOT = Path("data/clean")


def iter_book_dirs(all_books: bool, book_id: str | None) -> Iterable[Path]:
    if all_books and CLEAN_ROOT.exists():
        for p in sorted(CLEAN_ROOT.iterdir()):
            if p.is_dir():
                yield p
    elif book_id:
        yield CLEAN_ROOT / book_id
    else:
        yield CLEAN_ROOT / "SAMPLE_BOOK"


def remove_book_dir(book_dir: Path, dry: bool = False) -> None:
    if not book_dir.exists():
        return
    for p in book_dir.glob("*.json"):
        try:
            if dry:
                print(f"DRY: would remove {p}")
            else:
                p.unlink()
        except Exception as e:  # noqa: BLE001
            print(f"WARN: failed to remove {p}: {e}")
    # Optionally purge any nested chapter json (if future structure changes)
    chapters_dir = book_dir / "chapters"
    if chapters_dir.exists():
        for p in chapters_dir.glob("*.json"):
            try:
                if dry:
                    print(f"DRY: would remove {p}")
                else:
                    p.unlink()
            except Exception as e:  # noqa: BLE001
                print(f"WARN: failed to remove {p}: {e}")


def main(argv: list[str]) -> int:
    all_books = "--all" in argv
    dry = "--dry-run" in argv
    db_flag = "--db" in argv
    # Determine explicit book id if provided (first non-flag argument)
    book_arg = None
    for a in argv[1:]:
        if a.startswith("-"):
            continue
        book_arg = a
        break

    # If --db used without a book id default to SAMPLE_BOOK unless
    # --all is also set (then apply to each).
    any_found = False
    for bdir in iter_book_dirs(all_books, book_arg):
        if not bdir.exists():
            continue
        any_found = True
        book_id = bdir.name
        print(f"Cleaning {bdir} (dry={dry})")
        remove_book_dir(bdir, dry=dry)
        if db_flag and repository and get_session:
            if dry:
                print(f"DRY: would delete DB chapters for {book_id}")
            else:
                try:
                    with get_session() as session:  # type: ignore
                        deleted = repository.delete_chapters(  # type: ignore
                            session, book_id
                        )
                    print(
                        f"Deleted {deleted} DB chapter rows for {book_id}"
                    )
                except Exception as e:  # noqa: BLE001
                    print(f"WARN: DB purge failed for {book_id}: {e}")
    if not any_found:
        print("No matching book directories found to clean.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
