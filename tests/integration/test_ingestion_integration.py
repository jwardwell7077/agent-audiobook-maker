from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from abm.ingestion.ingest_pdf import PdfIngestPipeline, PipelineOptions


class _DummyExtractor:
    def extract_pages(self, _p: Path) -> list[str]:
        return ["Table of Contents\nChapter 1: One\nChapter 2: Two", "Chapter 1: One\nBody\n\nChapter 2: Two\nBody"]

    def assemble_output(self, pages: list[str], _opts: Any) -> str:
        return "\n\n".join(pages) + "\n"


def _monkeypatch_extractor(monkeypatch: pytest.MonkeyPatch) -> None:
    import abm.ingestion.ingest_pdf as mod

    monkeypatch.setattr(mod, "RawPdfTextExtractor", lambda: _DummyExtractor())


def test_pipeline_dev_mode_full_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _monkeypatch_extractor(monkeypatch)
    pipeline = PdfIngestPipeline()
    pdf_path = tmp_path / "Book.pdf"
    out_dir = tmp_path / "out"
    pipeline.run(pdf_path, out_dir, PipelineOptions(mode="dev"))
    assert (out_dir / "Book_raw.txt").exists()
    assert (out_dir / "Book_well_done.txt").exists()
    assert (out_dir / "Book_ingest_meta.json").exists()
    assert (out_dir / "Book_well_done.jsonl").exists()
    assert (out_dir / "Book_well_done_meta.json").exists()

    # Meta hashes present
    meta = json.loads((out_dir / "Book_ingest_meta.json").read_text(encoding="utf-8"))
    assert isinstance(meta.get("raw_sha256"), str)
    assert isinstance(meta.get("well_done_sha256"), str)

    out = capsys.readouterr().out
    assert "[DB STUB]" in out


def test_pipeline_prod_mode_no_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _monkeypatch_extractor(monkeypatch)
    pipeline = PdfIngestPipeline()
    pdf_path = tmp_path / "Book.pdf"
    out_dir = tmp_path / "out"
    result = pipeline.run(pdf_path, out_dir, PipelineOptions(mode="prod"))
    assert result == {}
    assert list(out_dir.glob("*")) == []
    out = capsys.readouterr().out
    assert "in-memory" in out
