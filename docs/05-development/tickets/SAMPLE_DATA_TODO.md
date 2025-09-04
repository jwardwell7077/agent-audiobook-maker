# TODO: Public Sample Data Set for Spans-First Pipeline

## Context

We need a small, fully public sample dataset to exercise the spans-first upstream (Blocks -> Spans -> Classify -> Attribute -> Casting -> Style). This must be reproducible, license-safe, and CI-friendly. The repo already whitelists data/books/SAMPLE_BOOK and related folders in .gitignore.

## Goals

- Minimal but representative sample book with 2–3 short chapters.
- Include source text, normalized chapters.json, and optional prebuilt "golden" artifacts (blocks/spans/spans_cls/spans_attr) for deterministic tests.
- Copyright-clean (synthetic or public domain) with LICENSE/ATTRIBUTION note.
- Small size for CI (\< 2 MB total, text-only; no audio).
- Tiny voice bank sample mapping narrator + 1–2 speakers.

## Deliverables

- data/books/SAMPLE_BOOK/
  - source_text/\*.txt and/or source_pdfs/synthetic_sample.pdf (optional)
  - classified/chapters.json (normalized; 0-based indices, chapter_number included)
- data/clean/SAMPLE_BOOK/\*\* (if applicable)
- data/casting/voice_bank.sample.json (tiny bank for tests)
- docs/README in sample folder with provenance and license
- Optional: output/SAMPLE_BOOK/chNN "golden" JSONL artifacts for unit tests (or a deterministic generator script)

## Tasks

- [ ] Create synthetic sample text with both dialogue and narration.
- [ ] Produce normalized chapters.json (0-based indices, chapter_number present).
- [ ] Run validator -> resolver -> classifier -> attribution to produce deterministic JSONL artifacts.
- [ ] Create voice_bank.sample.json (narrator + 2 character labels).
- [ ] Add README in the sample folder with license and structure.
- [ ] Add/adjust unit tests to consume SAMPLE_BOOK when present (skip if absent in CI where needed).
- [ ] Makefile targets: - sample.prepare (generate/refresh sample artifacts locally) - sample.clean (remove sample output artifacts)
- [ ] Ensure .gitignore keeps sample paths included and excludes heavy outputs (/output/).

## Acceptance Criteria

- Spans-first pipeline runs locally on SAMPLE_BOOK with no network calls.
- Unit tests using SAMPLE_BOOK pass deterministically on CI and locally.
- Repo size increase remains minimal (\< ~2 MB).
- Licensing/provenance documented; no restricted content.

## Notes

- Keep artifacts deterministic; avoid timestamps/volatile fields in golden files.
- Prefer plain text sources to avoid PDF parsing variability; include PDF only if helpful and small.
