# Architecture — Spans-first (Pre-SSML)

Goal: Move classification and attribution to spans before any SSML rendering seams. Deterministic artifacts at each stage, JSONL-only.

Pipeline stages:

- ChapterLoader → BlockSchemaValidator → MixedBlockResolver → SpanClassifier → SpanAttribution → (optional) StylePlanner → SpanIterator → SpanCasting → ArtifactOrchestrator

Notes:

- Deterministic IDs: sha1 over normalized text + stable keys.
- Records-only JSONL with `.meta.json` sidecars per stage.
- Internal indices 0-based; human reporting uses `chapter_number` 1-based.

Primary flow file: `examples/langflow/abm_spans_first_pipeline.v15.json`.

Outputs per stage (typical):

- blocks.jsonl → spans.jsonl → spans_cls.jsonl → spans_attr.jsonl → spans_cast.jsonl → spans_style.jsonl (optional)

Error modes:

- Validation failures raise; partial outputs avoided.
- Strict JSON/JSONL ingestion; `.txt` rejected at classifier CLI boundary.
