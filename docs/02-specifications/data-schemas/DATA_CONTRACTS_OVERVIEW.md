# Data Contracts — JSON/JSONL + Meta

- Records-only JSONL per stage; one object per line.
- Sidecar meta: `<name>.meta.json` with created_at, counts, source, and immutable.
- Deterministic IDs: `block_uid`/`span_uid` via sha1 of normalized content + stable keys.
- Indices: internal 0-based; `chapter_number` is 1-based for user display.
- Classifier CLI enforces `.json` or `.jsonl` input; `.txt` is rejected.

Artifacts (typical):

- blocks.jsonl (from BlockSchemaValidator)
- spans.jsonl (from MixedBlockResolver)
- spans_cls.jsonl (from SpanClassifier)
- spans_attr.jsonl (from SpanAttribution)
- spans_cast.jsonl (from SpanCasting)
- spans_style.jsonl (optional, from StylePlanner)

Classifier outputs:

- toc.json
- chapters.json (chapters.chapters[] with chapter_index, chapter_number, title, start_block, end_block, paragraphs)
- front_matter.json (span_blocks, paragraphs, warnings)
- back_matter.json (span_blocks, paragraphs, warnings)
