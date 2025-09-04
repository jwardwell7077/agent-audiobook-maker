from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import Any

import pytest

from abm.ingestion.pdf_to_raw_text import (
    RawExtractOptions,
    RawPdfTextExtractor,
    _default_output_for_input,
)


def test_extract_raises_on_invalid_newline(tmp_path: Path) -> None:
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    out = tmp_path / "x.txt"
    with pytest.raises(ValueError):
        RawPdfTextExtractor().extract(pdf, out, RawExtractOptions(newline="X"))


def test_extract_raises_on_missing_file(tmp_path: Path) -> None:
    out = tmp_path / "o.txt"
    with pytest.raises(FileNotFoundError):
        RawPdfTextExtractor().extract(tmp_path / "missing.pdf", out)


def test_extract_pages_and_assemble_with_stubbed_fitz(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Page:
        def __init__(self, lines: list[str]) -> None:
            self._lines = lines

        def get_text(self, mode: str) -> Any:
            if mode == "blocks":
                # return blocks as tuples [x0, y0, x1, y1, text]
                return [
                    (0, 0, 10, 10, "First block\nLine two"),
                    (0, 20, 10, 30, "Second block"),
                ]
            return "\n".join(self._lines)

    class _Doc:
        def __init__(self) -> None:
            self._pages = [_Page(["A", "B"]), _Page(["C"])]

        def __iter__(self):  # noqa: D401
            return iter(self._pages)

        def close(self) -> None:  # noqa: D401 - stub
            pass

    def _open(_path: str) -> Any:
        return _Doc()

    # Install stub fitz.open
    import fitz as real_fitz  # type: ignore

    monkeypatch.setattr(real_fitz, "open", _open)

    extractor = RawPdfTextExtractor()
    pages = extractor.extract_pages(Path("/tmp/whatever.pdf"))
    # pages are strings; ensure two pages
    assert isinstance(pages, list) and len(pages) == 2

    text = extractor.assemble_output(
        pages,
        RawExtractOptions(
            newline="\n",
            preserve_form_feeds=True,
            strip_trailing_spaces=True,
            artifact_compat=False,
        ),
    )
    # Expect a form-feed between pages and trailing newline
    assert "\f" in text and text.endswith("\n")


def test_extract_pages_handles_blocks_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Page:
        def get_text(self, mode: str) -> Any:  # noqa: D401 - stub
            if mode == "blocks":
                raise RuntimeError("no blocks")
            return "fallback text"

    class _Doc:
        def __iter__(self):  # noqa: D401
            return iter([_Page()])

        def close(self) -> None:  # noqa: D401
            pass

    import fitz as real_fitz  # type: ignore

    monkeypatch.setattr(real_fitz, "open", lambda _p: _Doc())
    pages = RawPdfTextExtractor().extract_pages(Path("/tmp/x.pdf"))
    assert pages == ["fallback text"]


def test_extract_page_text_blocks_handles_empty_and_missing_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Page:
        def get_text(self, mode: str) -> Any:  # noqa: D401 - stub
            if mode == "blocks":
                # include entries with missing text field and empty text to exercise continues
                return [
                    (0, 0, 1, 1),  # len<5 -> no text
                    (0, 2, 1, 3, "Hello"),
                    (0, 4, 1, 5, ""),  # empty text
                    (0, 6, 1, 7, "World"),
                ]
            return "ignored"

    class _Doc:
        def __iter__(self):  # noqa: D401
            return iter([_Page()])

        def close(self) -> None:  # noqa: D401
            pass

    import fitz as real_fitz  # type: ignore

    monkeypatch.setattr(real_fitz, "open", lambda _p: _Doc())
    ex = RawPdfTextExtractor()
    pages = ex.extract_pages(Path("/tmp/a.pdf"))
    assert pages == ["Hello\n\nWorld"]


def test_assemble_output_crlf_newlines() -> None:
    ex = RawPdfTextExtractor()
    out = ex.assemble_output(["A", "B"], RawExtractOptions(newline="\r\n", preserve_form_feeds=False))
    assert "\r\n\r\n" in out and out.endswith("\r\n")


def test_extract_pages_raises_on_cannot_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Install fitz.open that raises
    class _R:
        def open(self, *_a: Any, **_k: Any) -> Any:  # noqa: D401 - stub
            raise RuntimeError("boom")

    sys.modules["fitz"] = _R()  # type: ignore[assignment]
    with pytest.raises(ValueError):
        RawPdfTextExtractor().extract_pages(tmp_path / "file.pdf")


def test_cli_main_writes_output_with_stubbed_fitz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Prepare fake fitz
    class _Page:
        def get_text(self, mode: str) -> Any:
            if mode == "blocks":
                return [(0, 0, 1, 1, "Hello")]
            return "Hello"

    class _Doc:
        def __iter__(self):
            return iter([_Page()])

        def close(self) -> None:
            pass

    class _Fitz:
        def open(self, *_a: Any, **_k: Any) -> Any:
            return _Doc()

    orig_fitz = sys.modules.get("fitz")
    sys.modules["fitz"] = _Fitz()  # type: ignore[assignment]

    pdf_p = tmp_path / "in.pdf"
    pdf_p.write_bytes(b"%PDF-1.4\n")
    out_p = tmp_path / "out.txt"
    # Simulate CLI: python -m abm.ingestion.pdf_to_raw_text in.pdf out.txt
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    argv = [
        "python",
        str(pdf_p),
        str(out_p),
        "--newline",
        "\n",
    ]
    monkeypatch.setattr(sys, "argv", ["abm.ingestion.pdf_to_raw_text", *argv[1:]])
    # Ensure module is importable (sets __spec__)
    import importlib

    importlib.import_module("abm.ingestion.pdf_to_raw_text")
    with pytest.raises(SystemExit) as e:
        runpy.run_module("abm.ingestion.pdf_to_raw_text", run_name="__main__")
    assert e.value.code == 0
    assert out_p.exists() and out_p.read_text(encoding="utf-8").strip() == "Hello"
    # Restore fitz
    if orig_fitz is not None:
        sys.modules["fitz"] = orig_fitz
    else:
        sys.modules.pop("fitz", None)


def test_assemble_output_normalizations() -> None:
    extractor = RawPdfTextExtractor()
    pages = ["line 1  with  gaps  \nwrap-\nup", "Next\nparagraph  "]
    # With dedupe and dehyphenation, the hyphenated wrap is fixed, and the single newline is preserved (no space join)
    text = extractor.assemble_output(
        pages,
        RawExtractOptions(
            newline="\n",
            preserve_form_feeds=False,
            strip_trailing_spaces=True,
            dedupe_inline_spaces=True,
            fix_short_wraps=True,
        ),
    )
    assert "line 1 with gaps\n" in text
    assert "wrapup" in text  # dehyphenated
    # page separator should be blank line when no form-feeds
    assert "\n\n" in text


def test_default_output_for_input() -> None:
    assert _default_output_for_input(Path("/a/b/c.pdf")).name == "c.txt"
