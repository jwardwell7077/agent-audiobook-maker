from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import abm.ingestion.ingest_pdf as ingest


def test_default_out_dir_with_books_path(tmp_path: Path) -> None:
    p = tmp_path / "data" / "books" / "mybook" / "source_pdfs" / "x.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4\n")
    out = ingest._default_out_dir(p)
    assert out.as_posix().endswith("data/clean/mybook")


def test_default_out_dir_fallback_to_parent_clean(tmp_path: Path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    out = ingest._default_out_dir(p)
    assert out == p.parent / "clean"


def test_stub_db_insert_print_exception_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _boom(*_a: Any, **_kw: Any) -> None:
        calls.append("called")
        raise RuntimeError("print failed")

    monkeypatch.setattr("builtins.print", _boom)
    # Should not raise in either mode
    ingest._stub_db_insert(mode="dev", base_name="b", jsonl_path=Path("a.jsonl"), meta_path=Path("a_meta.json"))
    ingest._stub_db_insert(mode="prod", base_name="b", well_text="x", meta={})
    assert calls  # ensure our print replacement ran
