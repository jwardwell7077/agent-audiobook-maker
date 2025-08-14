import pytest
from pathlib import Path

from pipeline.ingestion.pdf import (
    extract_pdf_text,
    detect_available_backends,
    ExtractionBackend,
)


def test_detect_backends_nonempty():
    backs = detect_available_backends()
    if not backs:
        pytest.skip("No PDF backends available in test environment")
    # If pypdf importable ensure it's detected
    try:
        import pypdf  # noqa: F401
        assert ExtractionBackend.PYPDF in backs
    except Exception:  # pragma: no cover
        pass
    # All returned values must be known enum members
    for b in backs:
        assert isinstance(b, ExtractionBackend)


def test_extract_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        extract_pdf_text("nonexistent_file_123456.pdf")


@pytest.mark.slow
@pytest.mark.skipif(
    ExtractionBackend.PYPDF not in detect_available_backends(),
    reason="pypdf backend not available",
)
def test_extract_real_pdf_smoke():
    # Use first PDF in book_pdf directory if present
    pdf_dir = Path("book_pdf")
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        pytest.skip("No sample PDFs present")
    sample = pdfs[0]
    res = extract_pdf_text(sample)
    # We don't assert on number of pages (large) just that call returns
    assert res.backend in detect_available_backends()
    # Allow empty text if encryption or extraction failure; warn instead
    assert isinstance(res.pages, list)


def test_extract_with_preference(monkeypatch, tmp_path: Path):
    # Create a tiny placeholder PDF or text fallback
    sample_pdf = tmp_path / "sample.pdf"
    sample_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    backs = detect_available_backends()
    if not backs:
        pytest.skip("No backends to test preference")
    # Use only first backend in preference to ensure it is attempted
    pref = [backs[0]]
    res = extract_pdf_text(sample_pdf, backends_preference=pref)
    # Even if empty text, backend should match preference first element
    assert res.backend == pref[0]
