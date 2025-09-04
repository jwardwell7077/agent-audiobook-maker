# LangFlow Components Index (Upstream, pre-SSML)

This index reflects the current upstream components after the redesign (Blocks → Spans → Spans_Cls → Spans_Attr → Spans_Cast; optional Spans_Style). All indices are 0-based internally; chapter_number (1-based) is preserved for reporting.

## Core Pipeline Components

- abm_block_schema_validator.py — Validates block schema; writes blocks.jsonl + meta
- abm_mixed_block_resolver.py — Splits mixed blocks into spans; writes spans.jsonl + meta
- abm_span_classifier.py — Labels spans (dialogue/narration) deterministically
- abm_span_attribution.py — Attributes dialogue spans with confidence/evidence; writes spans_attr.jsonl + meta
- abm_span_casting.py — Maps speakers to voice_id with defaults; writes spans_cast.jsonl + meta
- abm_style_planner.py (optional) — Produces StylePlan per span; writes spans_style.jsonl + meta

## Orchestration & Utilities

- abm_artifact_orchestrator.py — Runs upstream stages and writes artifacts to output/\<book>/chNN
- abm_span_iterator.py — Iterates spans JSONL; surfaces confidence; supports thresholding for UI
- abm_data_config.py — Handles shared configuration
- deterministic_confidence.py — Deterministic confidence scorer helper

## To Be Removed / Legacy (post-P0)

- abm_enhanced_chapter_loader.py — Legacy “chunk” loader; replaced by unified chapter loader
- abm_two_agent_runner.py, abm_two_agent_runner_component.py — Legacy runners (replace with upstream/downstream runners)
- abm_results_aggregator.py, abm_results_to_utterances.py — Superseded by JSONL artifacts and generalized writers
- abm_speaker_attribution.py — Legacy attribution; use abm_span_attribution.py

## Notes

- All artifacts are JSONL with sidecar meta.json; deterministic hashing for IDs (sha1 over normalized keys).
- Orchestrator should stop at spans_cast.jsonl by default (or spans_style.jsonl if enabled).
- Confidence/evidence are emitted deterministically; knobs exposed via orchestrator.
