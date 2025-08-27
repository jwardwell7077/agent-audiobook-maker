from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from abm.ingestion.ingest_pdf import PdfIngestPipeline, PipelineOptions


class _DummyExtractor:
    def extract_pages(self, pdf_path: Path) -> list[str]:  # noqa: D401 - simple stub
        # Return two simple pages; pdf_path is unused (monkeypatched in tests)
        return ["Hello", "World"]

    def assemble_output(self, pages: list[str], _opts: Any) -> str:  # noqa: D401 - simple stub
        return "\n".join(pages) + "\n"


def _monkeypatch_extractor(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the extractor class used within the pipeline to avoid PDF dependency
    import abm.ingestion.ingest_pdf as mod

    monkeypatch.setattr(mod, "RawPdfTextExtractor", lambda: _DummyExtractor())


def test_ingest_dev_mode_writes_artifacts_and_stubs_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _monkeypatch_extractor(monkeypatch)

    pipeline = PdfIngestPipeline()
    pdf_path = tmp_path / "MyBook.pdf"  # name used for stems only
    # We do not touch filesystem for input PDF due to extractor monkeypatch
    out_dir = tmp_path / "out"

    opts = PipelineOptions(mode="dev")
    written = pipeline.run(pdf_path, out_dir, opts)

    # Expected artifact files
    raw = out_dir / "MyBook_raw.txt"
    wd = out_dir / "MyBook_well_done.txt"
    meta = out_dir / "MyBook_ingest_meta.json"
    jsonl = out_dir / "MyBook_well_done.jsonl"
    jsonl_meta = out_dir / "MyBook_well_done_meta.json"

    assert written["raw"] == raw and raw.exists()
    assert written["well_done"] == wd and wd.exists()
    assert written["meta"] == meta and meta.exists()
    assert written["jsonl"] == jsonl and jsonl.exists()
    assert written["jsonl_meta"] == jsonl_meta and jsonl_meta.exists()

    # Validate meta JSON fields
    meta_obj = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_obj["mode"] == "dev"
    assert isinstance(meta_obj.get("raw_sha256"), str) and len(meta_obj["raw_sha256"]) == 64
    assert isinstance(meta_obj.get("well_done_sha256"), str) and len(meta_obj["well_done_sha256"]) == 64

    # DB stub should print
    out = capsys.readouterr().out
    assert "[DB STUB]" in out and "Would insert JSONL" in out


def test_ingest_prod_mode_writes_no_artifacts_and_stubs_db_in_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _monkeypatch_extractor(monkeypatch)

    pipeline = PdfIngestPipeline()
    pdf_path = tmp_path / "MyBook.pdf"
    out_dir = tmp_path / "out"

    opts = PipelineOptions(mode="prod")
    written = pipeline.run(pdf_path, out_dir, opts)

    # No artifacts written in prod
    assert written == {}
    assert not list(out_dir.glob("*"))  # directory exists but should be empty

    out = capsys.readouterr().out
    assert "[DB STUB]" in out and "in-memory" in out


def test_ingest_missing_input_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate missing input by making extractor raise FileNotFoundError
    import abm.ingestion.ingest_pdf as mod

    class _Raiser:
        def extract_pages(self, _p: Path) -> list[str]:
            raise FileNotFoundError("missing")

        def assemble_output(self, *_args: Any, **_kwargs: Any) -> str:  # pragma: no cover - not reached
            return ""

    monkeypatch.setattr(mod, "RawPdfTextExtractor", lambda: _Raiser())

    pipeline = PdfIngestPipeline()
    with pytest.raises(FileNotFoundError):
        pipeline.run(Path("/does/not/exist.pdf"), Path("/tmp/out"), PipelineOptions(mode="dev"))
