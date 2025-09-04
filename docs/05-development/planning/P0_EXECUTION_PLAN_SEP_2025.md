# P0 Execution Plan – September 2025

Status: draft
Branch: snapshot-2025-08-31-wip
Related: planning/ROADMAP_SEP_2025.md, tickets/ATTRIBUTION_CONFIDENCE_TODO.md

## Purpose

Deliver the P0 items this week with clear sequencing, concrete tasks, acceptance criteria, and minimal risk.

## Scope (P0)

- Stabilize legacy CLI tests (TOC tolerance, stub import error, strict heading matches); decide Prologue/Epilogue policy.
- Add provisional confidence fields to `spans_attr.jsonl` + meta version bump (default score=0.5; gated flag).
- Implement deterministic confidence v1 (features, weights, normalization, tiebreak) + unit tests.
- LangFlow: confidence preview (histogram + threshold) and wire threshold into iterator/orchestrator.

## Sequencing and ETA

- Day 1 AM: Legacy CLI tests triage and fixes; set Prologue/Epilogue policy (skip or adapt).
- Day 1 PM: Provisional confidence fields + artifact meta bump; update tests.
- Day 2 AM: Deterministic confidence v1 implementation with unit tests.
- Day 2 PM: LangFlow confidence preview + threshold wiring; quick smoke on MVS ch01.

______________________________________________________________________

## 1) Legacy CLI tests stabilization

Goal: All legacy ingestion/classifier CLI tests pass or are explicitly and temporarily skipped with rationale.

Tasks

- Identify failing tests and categorize: TOC parsing tolerance, stub import/mocking, strict heading matches, runpy packaging issues.
- TOC tolerance: align parser to reverted behavior (fa99ab7) or relax test expectations to tolerate missing/partial TOC.
- Stub import error: provide stable test double hooks or adjust tests to use existing seams; avoid relying on undefined `_stub_db_insert`.
- runpy ImportError: run modules via package entry points or refactor CLI to expose a callable `main()` and import that in tests.
- Strict heading matches: update tests to reflect tolerant section detection (e.g., case/whitespace-insensitive, alternative headings).
- Prologue/Epilogue: either skip with a TODO and issue link, or encode a policy and adjust expectations.
- Ensure tests do not write to repo; use tmp paths and respect `.gitignore` for `/output/`.

Touchpoints

- tests/integration/**, tests/unit_tests/** (legacy CLI suites)
- src/\*\* (ingestion/classifier CLI modules)

Acceptance criteria

- Legacy CLI suites green locally.
- Only intentional skips remain, each with a short rationale and ticket link.
- No dependency on undefined stubs; tests are hermetic with temp dirs.

Risks & mitigations

- Hidden import side effects → convert to callable `main()` and import that.
- Over-constraining tests → prefer behavior-based assertions over string matching.

______________________________________________________________________

## 2) Provisional confidence fields + meta version bump

Goal: Add confidence scaffolding so downstream can consume it before v1 lands.

Tasks

- Define confidence schema: `confidence.score` (float \[0,1\]), `method` (string), optional `evidence` (list\[str\]).
- Update `ABMSpanAttribution` to emit `confidence.score=0.5`, `method="deterministic_v0"`.
- Bump artifact version in spans_attr sidecar meta; record `confidence_schema_version`.
- Update readers (iterator/casting) to accept and pass-through the new fields; no behavior change.
- Add/adjust unit tests to assert presence and bounds of `confidence.score`.

Touchpoints

- src/abm/lf_components/audiobook/abm_span_attribution.py
- Any meta writer utilities (artifact version)
- tests/unit_tests for spans_attr

Acceptance criteria

- 100% of spans in `spans_attr.jsonl` include confidence fields.
- Sidecar meta reflects version bump and schema note.
- Tests pass; no public API break.

Risks & mitigations

- Downstream assumptions about schema → treat fields as additive; keep backward compatibility.

______________________________________________________________________

## 3) Deterministic confidence v1

Goal: Reproducible confidence scoring with tunable weights and clear evidence labels.

Tasks

- Implement deterministic features: name proximity, continuity, narration cues, quote boundaries, block context, optional character priors.
- Create a small weights config (JSON/YAML) with sensible defaults; load via component param.
- Scoring: weighted sum → normalization to \[0,1\] (logistic or min-max); document choice.
- Tiebreaker: deterministic hash of `(span_uid, book_id)`; unit test tie scenarios.
- Threshold parameter (default 0.6) surfaced in orchestrator; mark low-confidence spans in meta summary.
- Tests: feature unit tests, scorer normalization, tie behavior, end-to-end emission of confidence with `method="deterministic_v1"`.

Touchpoints

- abm_span_attribution.py (or helper module for scoring)
- tests/unit_tests/test_span_attribution_confidence.py (new)
- Optional: config file under `configs/confidence_v1.json`

Acceptance criteria

- Unit tests cover happy path + ties; deterministic results across runs.
- Confidence emitted for all spans with `method="deterministic_v1"`.
- Quick smoke on MVS ch01 shows reasonable distribution (not all at extremes).

Risks & mitigations

- Overfitting weights → keep config external; allow quick tuning; plan evaluation in P1.

______________________________________________________________________

## 4) LangFlow confidence preview + threshold wiring

Goal: Make confidence visible and actionable in the UI and orchestration.

Tasks

- Add a lightweight preview node that summarizes confidence distribution (counts per bucket, min/mean/max) and prints a compact text/JSON summary.
- Expose `low_conf_threshold` control in orchestrator/iterator nodes and include confidence in iterator outputs for UI display.
- Optionally add a simple histogram output (text-based bins) to avoid vendor UI dependencies.
- Verify example flow updates and re-export example JSON.

Touchpoints

- src/abm/lf_components/audiobook/abm_artifact_orchestrator.py (threshold param, summary)
- src/abm/lf_components/audiobook/abm_span_iterator.py (surface confidence fields)
- examples/langflow/abm_spans_first_pipeline\*.json (updated wiring)

Acceptance criteria

- Running the example flow prints a confidence summary and respects the threshold parameter.
- Iterator outputs include confidence fields for each span.

Risks & mitigations

- UI rendering constraints → prefer text summaries; keep visuals minimal and robust.

______________________________________________________________________

## Deliverables

- Green legacy CLI tests or justified skips with tickets.
- Updated `spans_attr.jsonl` with confidence scaffolding + meta version bump.
- Deterministic confidence v1 with unit tests and default config.
- Updated example LangFlow flow showing confidence summary and threshold control.

## Out of Scope (P0)

- LLM fallback (planned P2/P3); evaluation reports beyond a smoke summary (planned P1).
