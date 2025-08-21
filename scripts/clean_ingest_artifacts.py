<<<<<<< HEAD
#!/usr/bin/env python3
"""Clean ingestion artifacts for a given book (default: SB).

Removes generated chapter and volume JSON files under data/clean/<book_id>
so you can perform a fresh ingestion run without stale artifacts.

Usage:
        python scripts/clean_ingest_artifacts.py            # clean SB (files)
    python scripts/clean_ingest_artifacts.py BOOK_ID    # clean specific book
    python scripts/clean_ingest_artifacts.py --all      # clean all books
    python scripts/clean_ingest_artifacts.py --db SB   # also purge DB rows

Safety: only touches data/clean; never deletes source_pdfs or DB files.
Use --dry-run to preview deletions.
"""

from __future__ import annotations

import sys
import sys as _sys
from collections.abc import Iterable
from pathlib import Path

try:  # optional DB ops; skip if DB not initialised
    from db import (
        get_session,  # type: ignore
        repository,  # type: ignore
    )
except Exception:  # noqa: BLE001
    get_session = None  # type: ignore
    repository = None  # type: ignore

CLEAN_ROOT = Path("data/clean")


def iter_book_dirs(all_books: bool, book_id: str | None) -> Iterable[Path]:
    """Yield candidate book directories to clean.

    Preference order: --all supplied, explicit book id, default SAMPLE_BOOK.
    """
    if all_books and CLEAN_ROOT.exists():
        for p in sorted(CLEAN_ROOT.iterdir()):
            if p.is_dir():
                yield p
    elif book_id:
        yield CLEAN_ROOT / book_id
    else:
        yield CLEAN_ROOT / "SB"


def remove_book_dir(book_dir: Path, dry: bool = False) -> None:
    """Remove generated chapter JSON files for a single book directory."""
    if not book_dir.exists():
        return
    for p in book_dir.glob("*.json"):
        try:
            if dry:
                _sys.stdout.write(f"DRY: would remove {p}\n")
            else:
                p.unlink()
        except Exception as e:  # noqa: BLE001
            _sys.stdout.write(f"WARN: failed to remove {p}: {e}\n")
    # Optionally purge any nested chapter json (if future structure changes)
    chapters_dir = book_dir / "chapters"
    if chapters_dir.exists():
        for p in chapters_dir.glob("*.json"):
            try:
                if dry:
                    _sys.stdout.write(f"DRY: would remove {p}\n")
                else:
                    p.unlink()
            except Exception as e:  # noqa: BLE001
                _sys.stdout.write(f"WARN: failed to remove {p}: {e}\n")


def main(argv: list[str]) -> int:
    """CLI entry point for cleaning ingest artifacts."""
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

    # If --db provided without a standalone book id we default to SB unless
    # --all is also set (then apply to each).
    any_found = False
    for bdir in iter_book_dirs(all_books, book_arg):
        if not bdir.exists():
            continue
        any_found = True
        book_id = bdir.name
        _sys.stdout.write(f"Cleaning {bdir} (dry={dry})\n")
        remove_book_dir(bdir, dry=dry)
        if db_flag and repository and get_session:
            if dry:
                _sys.stdout.write(f"DRY: would delete DB chapters for {book_id}\n")
            else:
                try:
                    with get_session() as session:  # type: ignore
                        deleted = repository.delete_chapters(  # type: ignore
                            session, book_id
                        )
                    _sys.stdout.write(f"Deleted {deleted} DB chapter rows for {book_id}\n")
                except Exception as e:  # noqa: BLE001
                    _sys.stdout.write(f"WARN: DB purge failed for {book_id}: {e}\n")
    if not any_found:
        _sys.stdout.write("No matching book directories found to clean.\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
=======
>>>>>>> 1774ed3 (chore: fresh-start: keep docs only)
