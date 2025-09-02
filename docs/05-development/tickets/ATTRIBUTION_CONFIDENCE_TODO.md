# Attribution Confidence: Understanding, Deterministic Scoring, then LLM

Status: planned
Owner: TBD
Related: docs/ADVANCED_SPEAKER_ATTRIBUTION.md, spans-first pipeline, `abm_span_attribution.py`, `spans_attr.jsonl`

## Goal

Establish a clear, auditable confidence score for speaker attribution on spans, implement a deterministic scorer that is reproducible and tunable, and optionally add an LLM-based enhancer for low-confidence or ambiguous cases.

## Why

- Improve trust and debuggability of attribution decisions.
- Enable thresholding, fallbacks, and better UX in LangFlow/preview nodes.
- Provide a stable baseline (deterministic) and a path to higher quality (LLM) without sacrificing reproducibility.

## Scope

- spans-first pre‑SSML pipeline, specifically `spans_attr.jsonl` and `abm_span_attribution.py`.
- No vendor lock-in; LLM usage is optional and gated behind flags.

## Current State (as of snapshot-2025-08-31)

- `ABMSpanAttribution` uses heuristic rules; confidence is not formalized.
- `spans_attr.jsonl` has attribution details but lacks a standardized `confidence` object.

## Target Data Contract Changes

- `spans_attr.jsonl` entries gain a `confidence` section and a `method` tag.
- Backward compatible: version bump in sidecar meta, with writer emitting `artifact_version`.

Example (single span):

```json
{
  "span_uid": "sha1:...",
  "text": "\"Where are you?\" she asked.",
  "attribution": {
    "speaker": "MARY"
  },
  "confidence": {
    "score": 0.83,
    "evidence": ["name_proximity", "continuity", "quote_boundary"],
    "calibration": "deterministic_v1"
  },
  "method": "deterministic_v1"
}
```

## Deterministic Phase (v1)

- Feature extraction (deterministic):
  - name proximity (character lexicon match within K tokens)
  - continuity (same speaker as previous dialogue span, penalize speaker runs)
  - narration cues (verbs of utterance: said, asked, replied, etc.)
  - punctuation/quote boundary patterns
  - block context (within-block speaker alternation bias)
  - character priors (optional, per-chapter frequency smoothing)
- Scoring:
  - Weighted linear score of features; normalize to [0,1] via logistic or min-max.
  - All weights configured in a small YAML/JSON so they can be tuned per-book if needed.
- Ties/ambiguity:
  - Stable tiebreak via deterministic hash of `(span_uid, book_id)` to select among equal candidates, ensuring reproducibility.
  - If normalized score < threshold (e.g., 0.6), mark as `LOW_CONF` and surface for fallback.
- Outputs:
  - `confidence.score` (float 0–1), `confidence.evidence` (feature names), `method="deterministic_v1"`.

## LLM Enhancement Phase (v2 optional)

- Usage pattern:
  - Trigger only when `confidence.score < threshold` OR on explicit override.
  - Prompt the LLM with: span text, surrounding spans, candidate speakers, and a strict JSON schema.
  - Temperature 0, max tokens small, constrained output (JSON Schema), deterministic vendor settings.
- Caching:
  - Cache key: content-hash of input payload + model/version → response.
  - Store cache in `output/{book}/.cache/attribution_llm/` (gitignored), with a meta report.
- Safety/Cost:
  - Dry-run mode; hard cap on requests; per-chapter budget.
- Outputs:
  - `method="llm_v1"`, `confidence.score`, `confidence.evidence` (e.g., "llm_rationale: continuity + explicit tag"), and `llm.model` in meta sidecar, not per-span.

## Evaluation Plan

- Datasets: mvs ch01–ch04, later SAMPLE_BOOK once available.
- Metrics:
  - Accuracy vs. curated gold labels (subset), macro/micro accuracy.
  - Calibration (Brier score, reliability diagram buckets).
  - Coverage of high-confidence predictions (fraction > 0.7) and error rate within high-confidence bucket.
  - Confusions between major characters.
- Procedure:
  - Implement a small notebook report and a CLI summary in `abm_artifact_orchestrator` for quick stats.
  - Holdout at least one chapter to avoid overfitting weights.

## Tasks

- [ ] Define confidence schema and versioning for `spans_attr.jsonl` and sidecar meta.
- [ ] Add provisional fields to `ABMSpanAttribution` (return `confidence.score`, default 0.5) and update tests.
- [ ] Implement deterministic features and a weighted scorer (`deterministic_v1`), with config file and unit tests.
- [ ] Add orchestrator/flow flags: `enable_llm=False`, `low_conf_threshold=0.6`.
- [ ] Add evaluation utilities (notebook cell + simple CLI) to compute accuracy/calibration vs. gold when present.
- [ ] Implement LLM fallback (structured JSON output, cache, retries), behind flag.
- [ ] Document wiring in LangFlow, including preview node of confidence distributions.
- [ ] Write migration notes in docs and bump artifact version in meta.

## Acceptance Criteria

- Deterministic scorer produces stable results (bit-for-bit) across runs, with unit tests covering tie cases.
- Confidence present for 100% of spans in `spans_attr.jsonl`.
- On a curated sample set, overall accuracy ≥ 85% with `confidence.score ≥ 0.7`; within `≥0.9` bucket, error rate ≤ 5%.
- LLM fallback improves accuracy on low-confidence spans by ≥ 5 points (absolute) with bounded cost.
- Documentation updated; LangFlow nodes surface confidence and thresholds.

## Risks & Mitigations

- Ambiguous dialogue with many minor characters → mitigate via character grouping and priors.
- Overfitting weights to a single book → use holdouts; keep weights configurable.
- LLM drift/vendor changes → pin versions; cache; keep deterministic as primary.

## Timeline (estimates)

- Deterministic v1: 1–2 days implementation + 0.5 day tuning.
- LLM fallback v1: 1 day integration + 0.5 day eval.
