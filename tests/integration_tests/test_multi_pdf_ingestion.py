import json
from pathlib import Path
import pytest

from pipeline.ingestion import multi_pdf


class DummyResult:
    def __init__(self, text: str = "Example chapter text"):
        self.text = text
        self.backend = "dummy"
        self.pages = [text]
        self.warnings = []


def test_ingest_pdf_files_raises_on_empty():
    with pytest.raises(ValueError):
        multi_pdf.ingest_pdf_files("bookX", [], out_root=Path("data/clean"))


def test_ingest_single_pdf_creates_artifacts(tmp_path: Path, monkeypatch):
    # Create dummy pdf file (content not actually parsed due to monkeypatch)
    pdf = tmp_path / "chapter01.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF")

    monkeypatch.setattr(
        multi_pdf, "extract_pdf_text", lambda p: DummyResult("Hello World")
    )
    out_root = tmp_path / "out"
    chapters = multi_pdf.ingest_pdf_files(
        book_id="demo", pdf_paths=[pdf], out_root=out_root
    )
    assert len(chapters) == 1
    ch_dir = out_root / "demo"
    json_file = ch_dir / "00000.json"
    txt_file = ch_dir / "00000.txt"
    jsonl_file = ch_dir / "chapters.jsonl"
    assert json_file.exists()
    assert txt_file.exists()
    assert jsonl_file.exists()
    # JSON contents
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["text"].startswith("Hello World")
    # JSONL line references json_path
    line = jsonl_file.read_text(encoding="utf-8").strip().splitlines()[0]
    rec = json.loads(line)
    assert rec["json_path"].endswith("00000.json")


def test_cli_usage_shows_help(monkeypatch, capsys):
    # Call main with insufficient args
    rc = multi_pdf.main([])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.err or "Usage:" in captured.out


def test_cli_ingest_flow(tmp_path: Path, monkeypatch, capsys):
    # Arrange PDF directory
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "ch1.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    (pdf_dir / "ch2.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    monkeypatch.setattr(
        multi_pdf,
        "extract_pdf_text",
        lambda p: DummyResult("Text for " + p.stem),
    )
    rc = multi_pdf.main(["bookY", str(pdf_dir), str(tmp_path / "out")])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Ingested 2 PDFs" in captured.out
    # Verify JSONL records count
    jsonl = (
        tmp_path / "out" / "bookY" / "chapters.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert len(jsonl) == 2
