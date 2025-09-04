# Alignment Check — Pre‑SSML Redesign (Sept 2025)

Source redesign: `docs/03-implementation/langflow/REDESIGN_PRE_SSML_PIPELINE.md`
Scope: Upstream (Blocks → Spans → Spans_Cls → Spans_Attr → Spans_Cast; optional Spans_Style)

## Snapshot summary

- Good: JSONL writers exist (blocks.jsonl, spans.jsonl, spans_cls.jsonl, spans_cast.jsonl). 0‑based indexing is referenced. Legacy two‑agent files are marked removed.
- Drift: Some legacy files still present (as stubs). Orchestrator is standardized on `abm_span_attribution.py`; `abm_speaker_attribution.py` remains as a deprecated breadcrumb.
- Docs: Roadmap/P0 plan files exist but are empty. Tickets for “middle_matter” and special‑character detection are ready.

## Component alignment matrix

- Block Schema Validator — Present (`abm_block_schema_validator.py`), writes blocks.jsonl → Aligned
- Mixed‑Block Resolver — Present (`abm_mixed_block_resolver.py`), writes spans.jsonl → Aligned
- Span Classifier — Present (`abm_span_classifier.py`) → Aligned (verify label/feature schema)
- Speaker Attribution — Present (`abm_span_attribution.py`); legacy `abm_speaker_attribution.py` is stubbed (deprecated) → No action until legacy flows are archived
- Casting — Present (`abm_span_casting.py`) → Aligned (voice mapping via voice_bank.json)
- Style Planner — Present (`abm_style_planner.py`) → Optional in P0
- Orchestrator — Present (`abm_artifact_orchestrator.py`) → Verify stage names/paths (mentions spans_attr.jsonl)
- Runners — Legacy two‑agent runner files still in tree as placeholders → Remove after P0

## Gaps and fixes

- Artifacts/Contracts
  - Verify 0‑based indices everywhere; add chapter_number (1‑based) where missing
  - Ensure deterministic hashing is consistent across stages (NFC, lower, collapse WS)

- Attribution path
  - Standardize on `abm_span_attribution.py`; keep `abm_speaker_attribution.py` only as deprecated placeholder until legacy flows are archived
  - Confirm output path name (spans_attr.jsonl) and orchestrator wiring

- Legacy cleanup
  - Delete or archive stubbed legacy files post‑P0 (two‑agent runner, enhanced loader)

- Small features agreed post‑redesign
  - Section Classifier: tail‑only “middle_matter” (deterministic)
  - Special‑character detection (ai‑system): detection only (<...> lines), in‑place tags

## Risks

- Mixed naming (spans_attr vs spans_cls additions) → clarify single source of truth
- Hidden 1-based indices in old code → add asserts

## Acceptance (P0)

- End-to-end upstream run produces: blocks.jsonl → spans.jsonl → spans_cls.jsonl → spans_attr.jsonl → spans_cast.jsonl (optionally spans_style.jsonl)
- Deterministic IDs/indexing; CI tests cover each stage
- Middle_matter and ai-system detection wired without expanding scope
