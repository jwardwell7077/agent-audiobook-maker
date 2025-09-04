from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from typing import Any

import pytest

import abm.ingestion.ingest_pdf as ingest


def test_build_meta_includes_wd_when_present(tmp_path: Path) -> None:
    pdf_p = tmp_path / "data" / "books" / "novel" / "src" / "book.pdf"
    pdf_p.parent.mkdir(parents=True)
    pdf_p.write_bytes(b"%PDF-1.4\n")
    raw = tmp_path / "raw.txt"
    raw.write_text("raw", encoding="utf-8")
    wd = tmp_path / "well.txt"
    wd.write_text("well", encoding="utf-8")
    meta = ingest._build_meta(pdf_p, tmp_path, raw, wd, ingest.PipelineOptions())
    assert meta["book"] == "novel"
    assert "raw_sha256" in meta and "well_done_sha256" in meta


def test_build_meta_without_wd_path(tmp_path: Path) -> None:
    pdf_p = tmp_path / "book.pdf"
    pdf_p.write_bytes(b"%PDF-1.4\n")
    raw = tmp_path / "r.txt"
    raw.write_text("x", encoding="utf-8")
    meta = ingest._build_meta(pdf_p, tmp_path, raw, None, ingest.PipelineOptions())
    assert "well_done_sha256" not in meta


def test_build_meta_ephemeral_books_and_no_books(tmp_path: Path) -> None:
    a = tmp_path / "data" / "books" / "series" / "bk.pdf"
    a.parent.mkdir(parents=True)
    a.write_bytes(b"%PDF-1.4\n")
    m1 = ingest._build_meta_ephemeral(a, tmp_path, ingest.PipelineOptions())
    assert m1["book"] == "series"

    b = tmp_path / "loose.pdf"
    b.write_bytes(b"%PDF-1.4\n")
    m2 = ingest._build_meta_ephemeral(b, tmp_path, ingest.PipelineOptions())
    assert m2["book"] is None


def test_cli_main_dev_and_prod_with_stubs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Stub dependency modules imported by ingest_pdf at import time
    class _StubExtractor:
        def extract_pages(self, _p: Path) -> list[str]:
            return ["A"]

        def assemble_output(self, pages: list[str], _opts: Any = None) -> str:  # type: ignore[name-defined]
            return "\n\n".join(pages)

    class _StubRawExtractOptions:
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - stub
            pass

    class _FakePdfToRawModule:
        RawPdfTextExtractor = _StubExtractor
        RawExtractOptions = _StubRawExtractOptions

    class _StubRowsToJSONL:
        def convert_text(
            self,
            text: str,
            base_name: str,
            out_dir: str | Path,
            ingest_meta_path: str | Path | None = None,
        ) -> dict[str, Path]:
            out_d = Path(out_dir)
            out_d.mkdir(parents=True, exist_ok=True)
            jl = out_d / (base_name + ".jsonl")
            jl.write_text(json.dumps({"index": 0, "text": text}) + "\n", encoding="utf-8")
            meta = out_d / (base_name + "_meta.json")
            meta.write_text(
                json.dumps({"block_count": 1, "source_well_done": str(out_d / (base_name + ".txt"))}),
                encoding="utf-8",
            )
            return {"jsonl": jl, "meta": meta}

    class _FakeWDModule:
        WellDoneToJSONL = _StubRowsToJSONL

    # Backup originals and inject stubs
    orig_pdf = sys.modules.get("abm.ingestion.pdf_to_raw_text")
    orig_wd = sys.modules.get("abm.ingestion.welldone_to_json")
    sys.modules["abm.ingestion.pdf_to_raw_text"] = _FakePdfToRawModule()  # type: ignore[assignment]
    sys.modules["abm.ingestion.welldone_to_json"] = _FakeWDModule()  # type: ignore[assignment]

    # Dev run: default out dir uses books/<book>
    pdf_p = tmp_path / "data" / "books" / "bk" / "src" / "x.pdf"
    pdf_p.parent.mkdir(parents=True)
    pdf_p.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(sys, "argv", ["abm.ingestion.ingest_pdf", str(pdf_p), "--mode", "dev"])
    with pytest.raises(SystemExit) as e0:
        runpy.run_module("abm.ingestion.ingest_pdf", run_name="__main__")
    assert e0.value.code == 0

    # Prod run: explicit out-dir
    out_d = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "abm.ingestion.ingest_pdf",
            str(pdf_p),
            "--mode",
            "prod",
            "--out-dir",
            str(out_d),
        ],
    )
    with pytest.raises(SystemExit) as e1:
        runpy.run_module("abm.ingestion.ingest_pdf", run_name="__main__")
    assert e1.value.code == 0

    # Restore originals to avoid polluting other tests
    if orig_pdf is not None:
        sys.modules["abm.ingestion.pdf_to_raw_text"] = orig_pdf
    else:
        sys.modules.pop("abm.ingestion.pdf_to_raw_text", None)
    if orig_wd is not None:
        sys.modules["abm.ingestion.welldone_to_json"] = orig_wd
    else:
        sys.modules.pop("abm.ingestion.welldone_to_json", None)
