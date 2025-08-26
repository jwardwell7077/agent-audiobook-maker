from __future__ import annotations

import importlib
import os
from pathlib import Path


def test_e2e_mvs_optional(tmp_path: Path) -> None:
    """Optional E2E test from PDF → text → classifier using mvs.

    Skips automatically when local dev assets are not available. This prevents
    relying on private/large files in CI while letting devs validate the whole
    pipeline locally.
    """
    try:
        import pytest  # local import to avoid unused when skipped by CI
    except Exception:  # pragma: no cover
        pytest = None  # type: ignore[assignment]

    from abm.ingestion.ingest_pdf import PdfIngestPipeline, PipelineOptions
    classifier_main = importlib.import_module(
        "abm.classifier.classifier_cli"
    ).main

    pdf = Path(
        "data/books/mvs/source_pdfs/MyVampireSystem_CH0001_0700.pdf"
    )
    # Only run when explicitly enabled to avoid long runtime in CI
    if os.getenv("ABM_E2E_MVS") != "1" or not pdf.exists():
        if ('pytest' in globals() and pytest is not None):
            reason = (
                "set ABM_E2E_MVS=1 and ensure mvs PDF exists to run"
            )
            pytest.skip(reason)
        return

    # Stage 1: PDF → Text (raw + well-done)
    out_dir = tmp_path / "ingest"
    opts = PipelineOptions(preserve_form_feeds=True, mode="both")
    written = PdfIngestPipeline().run(pdf, out_dir, opts)
    out_txt = written["well_done"] if "well_done" in written else written["raw"]

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

    # Stage 3 removed: Chapterizer is deprecated; classifier output is the source of truth.
    # Sanity: classifier outputs exist and are non-empty
    for name in (
        "toc.json",
        "chapters_section.json",
        "back_matter.json",
    ):
        p = out_dir / name
        assert p.exists() and p.stat().st_size > 0
