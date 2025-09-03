# Spans‑First Flow with Deterministic Confidence

This flow demonstrates the upstream spans‑first pipeline with deterministic confidence and a viewer threshold.

- Template: `tools/spans_first_confidence.flow.json`
- Components:
  - Block Schema Validator → Mixed Block Resolver → Span Classifier → Span Attribution (use_deterministic_confidence=true) → Span Iterator (dialogue_only=true, min_confidence_pct=75)

## Run it in LangFlow

1) Start LangFlow with your workspace mounted (example):

```bash
python scripts/run_langflow.sh
```

1. Import the flow JSON (`tools/spans_first_confidence.flow.json`).

2. Provide `blocks_data` to the validator (from a loader node or a minimal payload), then run.

## Tuning

- Attribution confidence
  - Toggle: `use_deterministic_confidence` (default: true)
  - Baselines: `base_confidence`, `unknown_confidence`

- Iterator filtering
  - `dialogue_only` to only show dialogue spans
  - `min_confidence_pct` to hide low‑confidence dialogue (e.g., 75)

## Notes

- The scorer is deterministic and explainable. Evidence appears under `attribution.evidence.confidence`.
- Orchestrator also supports a `min_confidence_pct` for chapter‑level filtering if you use it instead of the raw chain.
