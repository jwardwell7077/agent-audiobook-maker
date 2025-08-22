from __future__ import annotations

from pathlib import Path
import os
import importlib


def test_e2e_mvs_optional(tmp_path: Path) -> None:
    """Optional E2E test from PDF → text → classifier → chapterizer using mvs.

    Skips automatically when local dev assets are not available. This prevents
    relying on private/large files in CI while letting devs validate the whole
    pipeline locally.
    """
    try:
        import pytest  # local import to avoid unused when skipped by CI
    except Exception:  # pragma: no cover
        pytest = None  # type: ignore[assignment]

    pdf_to_text_main = importlib.import_module(
        "abm.ingestion.pdf_to_text_cli"
    ).main
    classifier_main = importlib.import_module(
        "abm.classifier.classifier_cli"
    ).main
    chapterizer_main = importlib.import_module(
        "abm.structuring.chapterizer_cli"
    ).main

    pdf = Path(
        "data/books/mvs/source_pdfs/MyVampireSystem_CH0001_0700.pdf"
    )
    # Only run when explicitly enabled to avoid long runtime in CI
    if os.getenv("ABM_E2E_MVS") != "1" or not pdf.exists():
        if (
            'pytest' in globals()
            and pytest is not None  # type: ignore[name-defined]
        ):
            reason = (
                "set ABM_E2E_MVS=1 and ensure mvs PDF exists to run"
            )
            pytest.skip(reason)
        return

    # Stage 1: PDF → Text
    out_txt = tmp_path / "mvs.txt"
    rc = pdf_to_text_main([
        str(pdf),
        str(out_txt),
        "--preserve-form-feeds",
    ])
    assert rc == 0 and out_txt.exists()

    # Sanity: file should be non-trivial
    content = out_txt.read_text(encoding="utf-8")
    assert len(content) > 10_000

    # Stage 2: Classifier
    out_dir = tmp_path / "classified"
    rc = classifier_main([str(out_txt), str(out_dir)])
    assert rc == 0
    # Artifacts exist
    for name in (
        "front_matter.json",
        "toc.json",
        "chapters_section.json",
        "back_matter.json",
    ):
        assert (out_dir / name).exists()

    # Stage 3: Chapterizer
    out_chapters = tmp_path / "chapters.json"
    rc = chapterizer_main([str(out_txt), str(out_chapters)])
    assert rc == 0 and out_chapters.exists()

    # Light validation
    data = out_chapters.read_text(encoding="utf-8")
    assert "\"chapters\"" in data
    # Expect the known chapter title to appear somewhere
    assert "Ability Level" in data
