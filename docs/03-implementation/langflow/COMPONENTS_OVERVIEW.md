# Components Overview (LangFlow)

Category: audiobook (custom components discovered from `src/abm/lf_components`).

- ABMChapterLoader (`src/abm/lf_components/audiobook/abm_chapter_loader.py`)
  - Loads `chapters.json` and can emit `blocks_data` for a selected chapter.
  - Autodiscovery paths: `data/clean/<book>/[classified|classified_jsonl]/chapters.json`.

- ABMBlockSchemaValidator (`src/abm/lf_components/audiobook/abm_block_schema_validator.py`)
  - Normalizes blocks, computes `block_uid`, writes `blocks.jsonl` + `blocks.meta.json`.

- ABMMixedBlockResolver (`src/abm/lf_components/audiobook/abm_mixed_block_resolver.py`)
  - Splits mixed blocks into spans; computes `span_uid`, writes `spans.jsonl` + meta.

- ABMSpanClassifier (`src/abm/lf_components/audiobook/abm_span_classifier.py`)
  - Labels spans (dialogue/narration); writes `spans_cls.jsonl` + meta.

- ABMSpanAttribution (`src/abm/lf_components/audiobook/abm_span_attribution.py`)
  - Heuristic speaker attribution; writes `spans_attr.jsonl` + meta.

- ABMStylePlanner (optional) (`src/abm/lf_components/audiobook/abm_style_planner.py`)
  - Vendor-neutral style plan per span; writes `spans_style.jsonl` + meta.

- ABMSpanIterator (`src/abm/lf_components/audiobook/abm_span_iterator.py`)
  - Iterates spans, supports windows and dialogue-only modes.

- ABMSpanCasting (`src/abm/lf_components/audiobook/abm_span_casting.py`)
  - Assigns voices from voice bank; writes `spans_cast.jsonl` + meta.

- ABMArtifactOrchestrator (`src/abm/lf_components/audiobook/abm_artifact_orchestrator.py`)
  - Convenience runner: validator → resolver → classifier → attribution (optional style).

Example flow: `examples/langflow/abm_spans_first_pipeline.v15.json`.
