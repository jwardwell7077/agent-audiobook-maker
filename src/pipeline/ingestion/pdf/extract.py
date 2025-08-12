"""PDF extraction backends with graceful degradation.

Design goals:
- Deterministic ordering of attempted backends.
- Minimal dependencies by default; heavy libs optional.
- Return structured result (pages list + combined text + metadata).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence
import shutil


class ExtractionBackend(str, Enum):
    PYPDF2 = "pypdf2"
    PDFMINER = "pdfminer"
    PDFTOTEXT = "pdftotext"


@dataclass
class PDFExtractionResult:
    backend: ExtractionBackend
    pages: List[str]
    text: str
    warnings: List[str]

    def join(self) -> str:  # convenience
        return self.text


def detect_available_backends() -> List[ExtractionBackend]:
    available: List[ExtractionBackend] = []
    try:  # PyPDF2
        import PyPDF2  # noqa: F401
        available.append(ExtractionBackend.PYPDF2)
    except Exception:  # pragma: no cover
        pass
    try:  # pdfminer
        import pdfminer  # noqa: F401
        available.append(ExtractionBackend.PDFMINER)
    except Exception:  # pragma: no cover
        pass
    if shutil.which("pdftotext"):
        available.append(ExtractionBackend.PDFTOTEXT)
    return available


def _extract_pypdf2(path: Path) -> Optional[PDFExtractionResult]:
    try:
        import PyPDF2
    except ImportError:  # pragma: no cover
        return None
    pages: List[str] = []
    warnings: List[str] = []
    try:
        with path.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                try:
                    txt = page.extract_text() or ""
                except Exception as e:  # pragma: no cover
                    warnings.append(f"page {i} extract error: {e}")
                    txt = ""
                pages.append(txt.strip())
    except Exception as e:  # pragma: no cover
        warnings.append(f"file read error: {e}")
    full = "\n\f\n".join(pages)
    return PDFExtractionResult(ExtractionBackend.PYPDF2, pages, full, warnings)


def _extract_pdfminer(path: Path) -> Optional[PDFExtractionResult]:
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
    except ImportError:  # pragma: no cover
        return None
    pages: List[str] = []
    warnings: List[str] = []
    try:
        for i, layout in enumerate(extract_pages(path)):
            texts: List[str] = []
            for element in layout:  # type: ignore
                if isinstance(element, LTTextContainer):
                    texts.append(element.get_text())
            pages.append("".join(texts).strip())
    except Exception as e:  # pragma: no cover
        warnings.append(f"pdfminer error: {e}")
    full = "\n\f\n".join(pages)
    return PDFExtractionResult(
        ExtractionBackend.PDFMINER, pages, full, warnings
    )


def _extract_pdftotext(path: Path) -> Optional[PDFExtractionResult]:
    if not shutil.which("pdftotext"):
        return None
    import subprocess

    warnings: List[str] = []
    try:
        # pdftotext outputs pages separated by form feed when -layout omitted
        result = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", str(path), "-"],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:  # pragma: no cover
            warnings.append(
                f"pdftotext exit {result.returncode}: {result.stderr.strip()}"
            )
        raw = result.stdout
        # Split on form feed boundaries heuristically
        pages = [p.strip() for p in raw.split("\f")]
        full = "\n\f\n".join(pages)
        return PDFExtractionResult(
            ExtractionBackend.PDFTOTEXT, pages, full, warnings
        )
    except Exception as e:  # pragma: no cover
        warnings.append(f"pdftotext error: {e}")
        return PDFExtractionResult(
            ExtractionBackend.PDFTOTEXT,
            [],
            "",
            warnings,
        )


def extract_pdf_text(
    path: str | Path,
    backends_preference: Sequence[ExtractionBackend] | None = None,
) -> PDFExtractionResult:
    """Extract text via first successful backend.

    Resolution order:
    - Provided `backends_preference` sequence if given.
    - Otherwise detected available backends in canonical order
      (PyPDF2, pdfminer, pdftotext).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    detected = detect_available_backends()
    order = (
        list(backends_preference)
        if backends_preference is not None
        else [
            b
            for b in [
                ExtractionBackend.PYPDF2,
                ExtractionBackend.PDFMINER,
                ExtractionBackend.PDFTOTEXT,
            ]
            if b in detected
        ]
    )
    attempts: List[str] = []
    for backend in order:
        attempts.append(backend.value)
        if backend is ExtractionBackend.PYPDF2:
            res = _extract_pypdf2(p)
        elif backend is ExtractionBackend.PDFMINER:
            res = _extract_pdfminer(p)
        else:
            res = _extract_pdftotext(p)
        if res and res.text.strip():
            if attempts[0] != backend.value:
                res.warnings.append(
                    "used fallback backend "
                    f"{backend.value}; earlier attempts: {attempts[:-1]}"
                )
            return res
    # None succeeded with non-empty text; return last (or empty) result stub
    return PDFExtractionResult(
        backend=order[-1] if order else ExtractionBackend.PYPDF2,
        pages=[],
        text="",
        warnings=[
            "no backend produced text"
            + (f" (attempts={attempts})" if attempts else "")
        ],
    )
