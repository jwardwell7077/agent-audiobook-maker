# Ticket: Fix failing tests — Ingest pipeline and Section Classifier

Status: Open  
Priority: P0 (blocking CI)  
Milestone: v0.1 KISS  
Labels: type:bug, prio:high, area:ingestion, area:classifier, tests

## Summary

Multiple tests related to the ingestion pipeline and section classifier are failing on the current branch. This ticket tracks the investigation and remediation to restore green CI for these areas without expanding scope beyond the KISS branch.

## Affected areas

- Ingestion v2 pipeline (raw → well_done → jsonl + meta sidecar)
- Ingest CLI behavior and meta sidecar naming/contents
- Section classifier contract for block-level classification

## Suspected failing tests (paths)

- Integration
  - `tests/integration/test_ingestion_integration.py`
  - `tests/integration/test_e2e_mvs_optional.py`
- Unit
  - `tests/unit_tests/test_ingest_pipeline.py`
  - `tests/unit_tests/test_ingest_pdf_meta_cli.py`
  - `tests/unit_tests/test_pdf_to_raw_text.py`
  - `tests/unit_tests/test_welldone_to_json.py`
  - `tests/unit_tests/test_welldone_to_json_meta.py`
  - `tests/unit_tests/test_section_classifier_block.py`

## Likely root causes (to confirm)

- API drift in ingest meta sidecar:
  - File naming expectations like `<Stem>_ingest_meta.json` (case and stem rules) not matching current output.
  - `options` and `ingested_from` fields present/absent or different types compared to tests.
- CLI entrypoints:
  - `abm.ingestion.ingest_pdf` and `abm.ingestion.pdf_to_raw_text` import-time behaviors and `__main__` execution may differ from tests’ expectations.
- Section classifier contract:
  - `abm.classifier.section_classifier.classify_blocks` return shape and error handling diverged from test contract.

## Acceptance criteria

- All targeted tests above pass locally and in CI (3.11/3.12) with no skips added.
- Ingest meta sidecar naming contract is deterministic and documented; tests validate against it.
- `WellDoneToJSONL` links `ingested_from` to discovered/provided sidecar as per tests.
- Section classifier `classify_blocks` returns the expected structure and raises on documented error cases; tests aligned with spec.
- No new runtime dependencies; scope remains KISS.

## Plan of action

1. Triage: capture exact failures

- Run focused subsets to gather tracebacks and mismatches.
- Document expected vs actual for filenames and JSON fields.

1. Ingest pipeline fixes

- Align sidecar naming to `<stem>_ingest_meta.json` where `stem` is base_name with `_well_done` removed.
- Ensure meta JSON includes fields: `book`, `source_well_done`, `block_count`, `ingested_from` (str|None), `options` (dict|None).
- Verify CLI behavior for `abm.ingestion.ingest_pdf` and `pdf_to_raw_text` under `python -m`.

1. WellDone converter fixes

- When `ingest_meta_path` provided and exists, set `ingested_from` to that path and load `options` from it; otherwise discovery behavior with graceful handling of invalid/missing JSON.

1. Section classifier contract

- Confirm current `classify_blocks` output shape and update either code or tests to match the documented spec in `docs/02-specifications/components/SECTION_CLASSIFIER_SPEC.md`.
- Add minimal unit coverage if gaps exist.

1. Documentation

- Update `docs/02-specifications/components/SECTION_CLASSIFIER_SPEC.md` and `docs/INGESTION_PIPELINE_V2.md` (or nearest equivalents) to lock the contract that tests assert.

## Repro/snippets

Run subsets during triage (examples):

- `pytest -q tests/unit_tests/test_ingest_pipeline.py -q`
- `pytest -q tests/unit_tests/test_welldone_to_json*.py -q`
- `pytest -q tests/unit_tests/test_ingest_pdf_meta_cli.py -q`
- `pytest -q tests/unit_tests/test_section_classifier_block.py -q`
- `pytest -q tests/integration/test_ingestion_integration.py -q`

## Out of scope

- Database integrations beyond stubbed paths (no DB required to pass tests).
- Multi-agent changes or orchestration frameworks.

## Deliverables

- Code fixes in ingestion pipeline and/or tests to re-align contracts.
- Adjusted/confirmed section classifier behavior + tests.
- Short doc updates summarizing the contracts.

## Checklist

- [ ] Capture failing outputs and list exact mismatches
- [ ] Fix ingest meta sidecar naming/fields
- [ ] Validate CLI `python -m` behavior for ingest and raw-text
- [ ] Ensure WellDone converter honors sidecar discovery and provided path
- [ ] Align section classifier output/errors with spec and tests
- [ ] Tests green locally (3.11) and in CI matrix (3.11/3.12)
- [ ] Docs updated where contracts are clarified
