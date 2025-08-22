from hashlib import sha256
from pathlib import Path

import pytest
from abm.ingestion.pdf_to_text import PdfToTextExtractor, PdfToTextOptions


def _hash_text(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def test_extract_happy_path(tmp_path: Path) -> None:
    pdf = Path("tests/data/books/war_of_the_worlds/war_of_the_worlds.pdf")
    if not pdf.exists():
        pytest.skip("sample PDF not present locally")
    out = tmp_path / "wotw.txt"
    PdfToTextExtractor().extract(pdf, out, PdfToTextOptions())
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert len(content) > 100
    assert content.endswith("\n")


def test_extract_determinism(tmp_path: Path) -> None:
    pdf = Path("tests/data/books/war_of_the_worlds/war_of_the_worlds.pdf")
    if not pdf.exists():
        pytest.skip("sample PDF not present locally")
    out1 = tmp_path / "a.txt"
    out2 = tmp_path / "b.txt"
    ext = PdfToTextExtractor()
    ext.extract(pdf, out1, PdfToTextOptions())
    ext.extract(pdf, out2, PdfToTextOptions())
    assert _hash_text(out1) == _hash_text(out2)


def test_extract_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PdfToTextExtractor().extract(
            "/no/such.pdf",
            tmp_path / "x.txt",
            PdfToTextOptions(),
        )


def test_newline_and_formfeed(tmp_path: Path) -> None:
    pdf = Path("tests/data/books/war_of_the_worlds/war_of_the_worlds.pdf")
    if not pdf.exists():
        pytest.skip("sample PDF not present locally")
    out = tmp_path / "wotw_ff.txt"
    PdfToTextExtractor().extract(
        pdf,
        out,
        PdfToTextOptions(preserve_form_feeds=True, newline="\r\n"),
    )
    content = out.read_text(encoding="utf-8")
    assert "\f" in content or "\r\n\r\n" in content


def test_dedupe_whitespace_toggle(tmp_path: Path) -> None:
    import fitz  # PyMuPDF

    pdf_path = tmp_path / "mini.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "hello   world\nsecond   line")
    doc.save(pdf_path)
    doc.close()

    out_true = tmp_path / "dedupe_true.txt"
    out_false = tmp_path / "dedupe_false.txt"
    ext = PdfToTextExtractor()

    ext.extract(pdf_path, out_true, PdfToTextOptions(dedupe_whitespace=True))
    ext.extract(pdf_path, out_false, PdfToTextOptions(dedupe_whitespace=False))

    t_true = out_true.read_text(encoding="utf-8")
    t_false = out_false.read_text(encoding="utf-8")

    assert "hello world" in t_true and "hello   world" not in t_true
    assert "hello   world" in t_false
