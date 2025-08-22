from pathlib import Path

import pytest
from abm.ingestion.pdf_to_text import PdfToTextExtractor, PdfToTextOptions


def test_invalid_newline_raises(tmp_path: Path) -> None:
    pdf = Path("tests/data/books/war_of_the_worlds/war_of_the_worlds.pdf")
    if not pdf.exists():
        pytest.skip("sample PDF not present locally")
    out = tmp_path / "o.txt"
    with pytest.raises(ValueError):
        PdfToTextExtractor().extract(pdf, out, PdfToTextOptions(newline="bad"))


def test_cli_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Import CLI lazily to avoid import cycles in tooling
    from abm.ingestion import pdf_to_text_cli

    # Nonexistent file should return specific nonzero codes
    out = tmp_path / "o.txt"
    code = pdf_to_text_cli.main(["/no/such.pdf", str(out)])
    assert code == 2


def test_invalid_pdf_raises_value_error(tmp_path: Path) -> None:
    # Create a non-PDF file with .pdf extension to trigger fitz open error
    bad_pdf = tmp_path / "not_a_pdf.pdf"
    bad_pdf.write_text("not a pdf", encoding="utf-8")
    out = tmp_path / "o.txt"
    with pytest.raises(ValueError):
        PdfToTextExtractor().extract(bad_pdf, out, PdfToTextOptions())


def test_cli_invalid_pdf_returns_3(tmp_path: Path) -> None:
    from abm.ingestion import pdf_to_text_cli

    bad_pdf = tmp_path / "not_a_pdf.pdf"
    bad_pdf.write_text("not a pdf", encoding="utf-8")
    out = tmp_path / "o.txt"
    code = pdf_to_text_cli.main([str(bad_pdf), str(out)])
    assert code == 3
