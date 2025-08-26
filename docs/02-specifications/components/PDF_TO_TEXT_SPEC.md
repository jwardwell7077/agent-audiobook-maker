# PDF → Text — Full Design Spec

Status: Draft
Owner: jon
Last updated: 2025-08-21

## Overview

Purpose: Extract clean UTF‑8 text from PDFs quickly and reproducibly for downstream segmentation and annotation using PyMuPDF (fitz) exclusively. Scope: local‑first, deterministic extraction from digital PDFs (non‑scanned). OCR is out of scope for this slice.

Assumptions and constraints

- KISS: no AI/LLM; pure rule‑based extraction.
- Deterministic: identical input PDF yields identical output bytes.
- Local‑first: no external services; no network calls.
- Performance: process 200‑page PDFs within seconds on CPU‑only.

## Diagrams

```mermaid
flowchart LR
  PDF[PDF file] -->|PyMuPDF (fitz)| EXTRACT[Extract pages]
  EXTRACT --> CLEAN[Normalize & clean]
  CLEAN --> TXT[Write .txt]
```text

Diagram source: [diagrams/pdf_to_text_flow.mmd](diagrams/pdf_to_text_flow.mmd)

UML (class)

```mermaid
%% See diagrams/pdf_to_text_uml.mmd for source
classDiagram
    direction TB

    class PdfToTextOptions {
      +bool dedupe_whitespace = true
      +bool preserve_form_feeds = false
      +str newline = "\\n"
      +bool use_blocks = true
      +bool insert_blank_line_between_blocks = true
      +int block_gap_threshold = 6
    }

    class PdfToTextExtractor {
      +extract(pdf_path: str, out_path: str, options: PdfToTextOptions) -> None
      -_read(pdf_path: str) -> list[str]
      -_clean(pages: list[str], options: PdfToTextOptions) -> str
      -_write(out_path: str, text: str) -> None
    }

    PdfToTextExtractor --> PdfToTextOptions
```text

## Contracts

Inputs

- pdf_path: Path to an existing .pdf file.
- options (optional):
  - dedupe_whitespace: bool (default true)
  - preserve_form_feeds: bool (default false)
  - use_blocks: bool (default true) – enable block-aware extraction to preserve layout-driven paragraph breaks.
  - insert_blank_line_between_blocks: bool (default true) – add a blank line between blocks when vertical gaps exceed threshold.
  - block_gap_threshold: int (default 6) – vertical gap threshold (pixels/points per PyMuPDF units) that defines a block break.

Outputs

- txt_path: Path to output .txt file (UTF‑8, Unix newlines).
- stdout/stderr: minimal structured log lines.

Invariants and guarantees

- UTF‑8 encoding, newline = "\n".
- Page order preserved; a single form feed ("\f") between pages when preserve_form_feeds=true, else a blank line.
- When use_blocks=true, intra-page blocks are joined with explicit blank lines when insert_blank_line_between_blocks=true and the vertical gap between their bounding boxes exceeds block_gap_threshold.
- No PDF object text reordering beyond library defaults; we do not attempt multi‑column reconstruction in this slice.

Error modes and edge cases

- FileNotFoundError: pdf_path missing.
- ValueError: not a PDF (magic mismatch) or encrypted without password.
- Empty pages: allowed; we still emit separators if configured.
- Truncated/corrupt PDF: surface a clean exception; no partial writes unless `--force` flag (deferred).

## Requirements

1. R-QUALITY-GATE: Component passes the quality gate (ruff clean, 100% Google-style docstrings, 100% test coverage for the component path).
2. R-PERF-BASELINE: 200pp text‑only PDF processes in < 10s on CPU (informational; validate locally and note in DEVELOPMENT_JOURNEY.md).
3. R-DETERMINISM: Re-running extraction on identical input produces byte-identical .txt output.

## Task Plan

- [ ] Implement `src/ingestion/pdf_to_text.py` with a small `PdfToTextOptions` dataclass and `extract(pdf_path, out_path, options)` using PyMuPDF (fitz).
- Deprecated: Use `python -m abm.ingestion.ingest_pdf <pdf> --out-dir <dir> [--mode dev] [--preserve-form-feeds]` instead of the old pdf_to_text_cli.
- [ ] Tests: golden samples with tiny fixture PDFs; determinism test; encrypted/invalid file tests.
- [ ] Wire into Makefile optional target `make pdf_to_text FILE=... OUT=...`.

## Test Plan (pytest)

- test_happy_path_small_pdf: extracts expected text, UTF‑8, newline policy respected.
- test_determinism_same_input_same_output: hash(txt) stable across runs.
- test_nonexistent_file_raises: clean error.
- test_encrypted_pdf_raises: clean error. (optional)
- test_preserve_form_feeds_inserts_formfeed: when enabled, page separators are form feeds.

Fixtures/data strategy

- Include 2–3 tiny PDFs under `tests/fixtures/pdfs/` (generated locally) to avoid license issues.
- Hash expected outputs stored as `.sha256` alongside fixtures.

Coverage/docstrings

- 100% coverage on `src/ingestion/pdf_to_text.py`.
- Interrogate at 100%; public functions/classes documented with Google‑style docstrings.

## Out of Scope

- OCR for scanned PDFs (Tesseract/PaddleOCR) — separate spec.
- Multi‑column/figure/table semantic reconstruction.
- Heuristic heading detection (handled in later segmentation component).

## Open Questions

- Do we prefer pdfplumber over pdfminer.six as the “fallback” for line ordering? Start with pdfminer.six due to stability.
- Should we emit a sidecar JSON with page offsets for downstream alignment? Likely yes in the next slice.
