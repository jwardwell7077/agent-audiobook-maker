# ABM Roadmap – September 2025

Status: draft Branch: snapshot-2025-08-31-wip Related tickets: tickets/ATTRIBUTION_CONFIDENCE_TODO.md

## Priorities

### P0 – Critical (this week)

- Stabilize legacy CLI tests (TOC tolerance, stub import error, strict heading matches); decide Prologue/Epilogue policy.
- Add provisional confidence fields to `spans_attr.jsonl` + meta version bump (default score=0.5; gated flag).
- Implement deterministic confidence v1 (features, weights, normalization, tiebreak) + unit tests.
- LangFlow: confidence preview (histogram + threshold) and wire threshold into iterator/orchestrator.

### P1 – High (near-term user value)

- Evaluation utilities: notebook + CLI for accuracy/calibration; curate small gold set (MVS ch01–ch02).
- SAMPLE_BOOK: minimal sample + golden artifacts.
- LangFlow UX polish: output_dir inference, status messages, orchestrator toggles, preview nodes.
- Orchestrator flags: `enable_llm`, `low_conf_threshold`, and reporting in meta.

### P2 – Medium (quality and coverage)

- LLM fallback for low-confidence spans: schema-constrained JSON, cache, budget caps.
- CI checks on artifacts: schema/version/count sanity.
- Docs: migration notes and LangFlow wiring for confidence + fallback.

### P3 – Later (enhancements)

- Confidence calibration (isotonic/logistic) and reliability report.
- Voice selection tweaks using confidence and character priors.
- Revisit and unskip Prologue/Epilogue test after policy alignment.
- Iterator improvements: batch size control and streaming previews.

## Milestones

- M1 (Week 1): CLI tests green, deterministic confidence v1 landed, LangFlow preview wired.
- M2 (Week 2): Eval notebook/CLI, SAMPLE_BOOK + golden artifacts, UX polish.
- M3 (Week 3): LLM fallback behind flag + cache, CI artifact checks, docs completed.

## Notes

- Keep deterministic as the primary path; LLM is gated and cached.
- All new artifact fields must be versioned and documented.
- Prefer tiny, focused PRs; add tests alongside behavior changes.
