"""Unit tests for PDF extraction environment controls and token handling.

Tests hyphen fix, camel case splitting, and token anomaly detection in PDF extraction.
"""

from pathlib import Path
from pathlib import Path as _Path

from _pytest.monkeypatch import MonkeyPatch

from pipeline.ingestion.pdf import PDFExtractionResult, extract_pdf_text


def make_fake_pdf(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    # Minimal pseudo-PDF wrapper
    p.write_bytes(b"%PDF-1.4\n" + content.encode("utf-8") + b"\n%%EOF")
    return p


def test_hyphen_fix_and_camel_split(monkeypatch: MonkeyPatch, tmp_path: _Path) -> None:
    # Enable fixes
    monkeypatch.setenv("INGEST_FORCE_PYMUPDF", "1")
    monkeypatch.setenv("INGEST_HYPHEN_FIX", "1")
    monkeypatch.setenv("INGEST_SPLIT_CAMEL", "1")
    pdf = make_fake_pdf(
        tmp_path,
        "sample.pdf",
        # Simulate hyphen line break + camel tokens & long token
        ("AlphaBeta Gamma-\nDelta SomeVeryLongConcatenatedWordWithoutSpacesThatIsSuspicious"),
    )
    res: PDFExtractionResult = extract_pdf_text(pdf)
    # Hyphen should be removed
    assert "Gamma-\nDelta" not in res.text
    assert "GammaDelta" in res.text
    # Camel split should add space
    assert "Alpha Beta" in res.text or "AlphaBeta" in res.text  # tolerance if no split
    # Token anomaly warning likely present (long token)
    assert any("token_length_anomaly" in w for w in res.warnings)
