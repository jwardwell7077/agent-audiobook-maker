# Ingestion v2: Proposed source code improvements (tests-only branch)

Owner: docs-and-tests branch

Date: 2025-08-27

Status: Draft proposals — do NOT implement on this branch

This document captures small, non-breaking source improvements observed while writing tests and docs. These are suggestions for a follow-up implementation branch.

## Scope and intent

- Keep current behavior stable for this branch.
- Document low-risk changes that improve clarity, observability, or correctness.
- Provide tiny contracts and acceptance checks to ease future PR review.

## 1) Add `# pragma: no cover` to CLIs’ main-guards

Files: `src/abm/ingestion/ingest_pdf.py`, `src/abm/ingestion/welldone_to_json.py`, `src/abm/ingestion/raw_to_welldone.py`, `src/abm/ingestion/pdf_to_raw_text.py`

Rationale:

- Our tests use module-level functions; invoking via `python -m` is exercised in a couple of CLI smoke tests. Coverage drops a few tenths due to `if __name__ == "__main__":` blocks. Marking these with `# pragma: no cover` keeps coverage signal focused on logic.

Acceptance:

- Coverage reports no longer count the `__main__` blocks.
- No change in runtime behavior.

## 2) WelldoneToJSONL: sidecar autodiscovery guardrails

File: `src/abm/ingestion/welldone_to_json.py`

Current behavior (tested):

- If `ingest_meta_path` is falsy, the code will try to infer a sidecar JSON near the `well_done.txt`, or infer book root using a `clean/` parent.

Improvements:

- Log (or return in meta) which path was chosen for sidecar (explicit, sibling, or inferred parent). This aids debugging silent mismatches.
- When multiple JSON files are nearby, prefer `*_meta.json` naming; otherwise, pick deterministic (lexicographic) to avoid flakiness.

Acceptance:

- `build_meta_for_wd()` returns `meta_source`: one of `"explicit" | "sibling" | "inferred" | "none"` and `meta_path` string when present.
- Unit tests assert determinism when multiple candidates are present.

## 3) RawToWellDone: option interplay clarity

File: `src/abm/ingestion/raw_to_welldone.py`

Observation:

- With `strip_trailing_spaces=False` but `dedupe_inline_spaces=True` (default), trailing double spaces at EOL can collapse depending on reflow path. This surprised some test expectations.

Improvements:

- Document in the `WellDoneOptions` docstring that `dedupe_inline_spaces=True` will also affect EOL runs of spaces.
- Consider an additional flag `preserve_eol_runs: bool = False` if strict preservation at line ends is desired while still deduping intra-line spaces.

Acceptance:

- Updated docstring explains the interaction.
- Optional: new flag plumbed and tested.

## 4) Section classifier: clearer error taxonomy and front-matter claim

File: `src/abm/classifier/section_classifier.py`

Current behavior (tested):

- TOC is detected over a sliding window and requires 2+ TOC-like lines; some mixed-block edge cases produce errors that differ from initial expectations.
- Front matter between TOC and first chapter is not currently claimed; warnings list unclaimed indices.

Improvements:

- Introduce specific error codes/messages (e.g., `TOCNotFound`, `InsufficientTOCItems`, `ChapterHeadingNotFound`, `MultipleHeadingsInBlock`) to simplify test assertions and UX.
- Optionally claim preface/front-matter blocks that sit between TOC and first chapter (if not part of TOC span) into `front_matter.paragraphs`.

Acceptance:

- Exceptions subclass `ValueError` with `.code` attribute or use small dataclasses.
- Unit tests can assert on `.code` rather than fragile strings.
- If front-matter claiming is enabled, tests expecting empty front matter are updated accordingly in the implementation branch.

## 5) `ingest_pdf` CLI: explicit dev/prod modes in help

File: `src/abm/ingestion/ingest_pdf.py`

Improvements:

- Ensure `--dev` vs `--prod` modes are clearly documented in `argparse` help; include what artifacts are written and which steps are stubbed.
- Return non-zero exit on invalid combinations (e.g., db flags in dev mode) with a concise message.

Acceptance:

- `python -m abm.ingestion.ingest_pdf -h` displays the above.
- CLI returns 2 on bad args, 1 on runtime errors.

## 6) Minor typing/doc polish

- Add `from __future__ import annotations` consistently.
- Add return type annotations for main helpers.
- Tighten a few regexes with `re.MULTILINE` where line-anchored semantics are intended explicitly.

Acceptance:

- mypy/pyright clean (informational), no runtime change.

______________________________________________________________________

Follow-up: Create an `implementation` branch (e.g., `ingestion-v2-polish`) to carry these edits with focused PRs per module. This doc serves as the checklist.
