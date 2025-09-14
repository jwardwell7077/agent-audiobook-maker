# Docs-and-Tests Branch Plan (Ingestion v2 + JSONL-first Classifier)

Purpose: Restore and update documentation and pytest coverage to reflect the new ingestion v2 pipeline and the updated JSONL-first Section Classifier. Scope limited to docs and tests (no feature changes).

## Branch

- Name: docs-and-tests
- Base: origin/langflow-multi-implement

## Context Snapshot

### Ingestion v2

File: ingest_pdf.py

Modes redefined:

- dev (default): writes all artifacts + DB insert stub

Outputs:

- \[STEM\]\_raw.txt

- \[STEM\]\_well_done.txt

- \[STEM\]\_ingest_meta.json

- \[STEM\]\_well_done.jsonl

- \[STEM\]\_well_done_meta.json

- Prints "\[DB STUB\] Would insert …"

- prod: writes no artifacts; DB insert stub only (in-memory)

PgInserter temporarily removed from ingest orchestrator; placeholder \_stub_db_insert with TODO for real DB.

CLI: --mode dev|prod, --out-dir, preserve well-done options; --emit-jsonl kept only for compatibility but ignored.

### Raw-to-well-done

File: raw_to_welldone.py

- Paragraph-first normalization with reflow/dehyphenate/dedupe/strip.
- Heuristics: TOC bullet splitting; optional heading split capability by code options (flags not exposed yet).

### JSONL conversion

File: welldone_to_json.py

- One JSON object per block, with sidecar meta linking ingest meta.

### Classifier (JSONL-first)

Files:

- classifier_cli.py (Argparse CLI; sources: .jsonl, .txt, and postgres stub; flags: --meta, --verbose)
- section_classifier.py (deterministic, block-based classifier)

Multipass TOC→chapter mapping:

- exact normalized title match
- ordinal match (decimal or Roman)
- relaxed prefix/fuzzy (small Levenshtein)

Separator handling: optional single-character separator with whitespace around it in both TOC and body headings.

TOC parsing constrained to a fixed lookahead (up to 5 blocks).

Recognizes Prologue/Epilogue; enforces monotonic chapter order; one heading per block.

Verified on a local private JSONL; do not process copyrighted works.

### Deprecated/legacy

Old ingestion tools and chapterizer are deprecated. Some legacy files may still exist; treat them as deprecated and update docs/tests to the v2 flow.

## What ingestion does now (succinct)

- Orchestrates PDF → raw → well-done → JSONL.
- dev mode writes all artifacts and prints a DB stub insert message.
- prod mode writes no artifacts and prints a DB stub insert message (in-memory).
- JSONL is the canonical downstream format for classifier and beyond.

## Doc Tasks

Update doc indices to reference v2:

- Link INGESTION_PIPELINE_V2.md from README.md and top-level README.md.
- Add deprecation notes to older specs: docs/PDF_TO_TEXT_SPEC.md, docs/TXT_TO_JSON_SPEC.md, and any CLI docs that mention chapterizer or legacy tools; point to v2.
- Note the new mode semantics (dev vs prod) and DB stub; remove “emit-jsonl” guidance (now tied to mode, dev only).
- Add a short “JSONL schema” quick reference (index, text) and how meta files relate.

Classifier docs:

- Reference SECTION_CLASSIFIER_SPEC.md and confirm shapes:
  - toc.json, chapters.json, front_matter.json, back_matter.json
  - Zero-based, inclusive spans; paragraphs array includes heading block at index 0.
- Add a subsection describing multi-pass matching and separator handling.
- Document ordinal fallback scenario using the “Chapter 3: Miltary School” example.

Stubs and TODOs:

- Call out that DB insertion/import are stubbed; include TODOs and expected interfaces when DB is available (e.g., document IDs or meta-based lookups).
- Include a short “migration notes” section describing what changed from the previous approach.

## Pytest Tasks

Test data

- Use a local private JSONL (e.g., data/clean/private_book/*_well_done.jsonl) as primary fixtures.
- If needed, create tiny synthetic fixtures under tests/data/ with minimal blocks for unit tests.

Ingestion tests

- dev mode: Run ingest on a small PDF fixture or mock the extractor; assert all artifacts exist and that a “\[DB STUB\]” message is printed. Validate JSONL/meta sanity.
- prod mode: Ensure no artifacts are written. Confirm “\[DB STUB\]” message with in-memory indicator is printed.
- Validate meta fields: book, source_pdf, mode, options present; sha256 on raw; well_done references present in dev.
- Error handling: missing input file generates non-zero exit and clear message.

Classifier tests

- JSONL load path: Verify correct block count and that blocks are treated as zero-based indices by content order.
- TOC detection: Positive case with TOC heading and ≥2 items in lookahead. Constrained lookahead does not swallow body headings.
- Chapter mapping multi-pass: Exact title match; Ordinal fallback (simulate “Miltary” vs “Military”); Relaxed match (prefix/fuzzy) when no ordinal is present.
- Error modes: Multiple headings in one block → raises. TOC entry cannot be matched → raises. Insufficient TOC-like items → raises.
- Output shape: toc.json, chapters.json, front/back matter shapes and inclusive spans. Heading block appears as paragraphs\[0\] for chapters.

CLI tests (lightweight)

- classifier_cli: .jsonl sources, .txt sources, “postgres” stub with --meta path; --verbose prints counts.
- ingest_pdf CLI: modes dev/prod; verify file outputs vs none and printed stub.
- Usage errors: missing args, nonexistent files.

Lint/Docs

- Fix markdown lint warnings across new docs (blank lines around lists, etc.).
- Ensure import order and slice spacing comply with linters.

## Acceptance Criteria

Docs:

- Top-level README and docs/README link to INGESTION_PIPELINE_V2.md.
- Deprecated docs have clear notes and redirection.
- Classifier spec mentions multi-pass logic and separator handling.

Tests:

- Pytest suite green locally and in CI.
- Tests cover ingestion dev/prod mode outputs, classifier multi-pass, and error modes.
- CLI smoke tests run without network or DB.

CI:

- Lint and tests run on the branch; no regressions.

## Checklist

- [ ] Link INGESTION_PIPELINE_V2.md from README.md and top-level README.md.
- [ ] Add deprecation notes to older ingestion docs and point to v2.
- [ ] Update classifier docs to include multi-pass and separator behavior.
- [ ] Add a brief JSONL format reference, including meta linkage.
- [ ] Add pytest fixtures for JSONL (small synthetic) and optional minimal PDF.
- [ ] Ingestion dev mode test: artifacts present + DB stub printed.
- [ ] Ingestion prod mode test: no artifacts + DB stub printed (in-memory).
- [ ] Meta validation tests: required fields and hashes in dev.
- [ ] Classifier tests: TOC detection, constrained lookahead, chapter mapping (exact/ordinal/relaxed).
- [ ] Classifier error tests: multiple headings, unmatched TOC entry, insufficient TOC items.
- [ ] CLI tests: classifier_cli (.jsonl/.txt/postgres stub with --meta; --verbose), ingest_pdf (--mode dev/prod).
- [ ] Fix any markdown lint issues across new/updated docs.
- [ ] Ensure imports/slices pass lint in scripts touched by tests.
- [ ] Update CI to run pytest and linters on this branch (if not already).

## Notes

- Only process private/local fixtures; skip copyrighted works.
- Keep database interactions stubbed; no real DB calls.
- Avoid feature changes in this branch; if gaps are found, capture as TODOs and file separate issues.
- Use this as the branch PR description or an issue body to coordinate the docs-and-tests effort end-to-end.
