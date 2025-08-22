from pathlib import Path

import pytest
from abm.ingestion import pdf_to_text_cli


def test_cli_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf = Path("tests/data/books/war_of_the_worlds/war_of_the_worlds.pdf")
    if not pdf.exists():
        pytest.skip("sample PDF not present locally")
    out = tmp_path / "o.txt"
    monkeypatch.setenv("PYTHONWARNINGS", "default")
    code = pdf_to_text_cli.main([str(pdf), str(out), "--preserve-form-feeds"])  # type: ignore[arg-type]
    assert code == 0
    assert out.exists() and out.stat().st_size > 0


def test_cli_invalid_path(tmp_path: Path) -> None:
    out = tmp_path / "o.txt"
    code = pdf_to_text_cli.main(["/no/such.pdf", str(out)])
    assert code != 0
