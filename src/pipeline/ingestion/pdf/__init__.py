"""PDF ingestion utilities.

Provides layered extractors with fallbacks:
1. PyPDF2 (fast, lightweight) for raw text.
2. pdfminer.six for layout-aware extraction (optional heavy).
3. Fallback to 'pdftotext' CLI if installed.

Expose unified `extract_pdf_text` that returns pages list and full text.
"""

from __future__ import annotations

from .extract import (
    ExtractionBackend,
    PDFExtractionResult,
    detect_available_backends,
    extract_pdf_text,
)

__all__ = [
    "extract_pdf_text",
    "PDFExtractionResult",
    "ExtractionBackend",
    "detect_available_backends",
]
