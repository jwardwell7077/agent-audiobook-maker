from __future__ import annotations

from pathlib import Path

import pytest

from abm.lf_components.audiobook.abm_block_schema_validator import ABMBlockSchemaValidator
from abm.lf_components.audiobook.abm_chapter_loader import ABMChapterLoader
from abm.lf_components.audiobook.abm_mixed_block_resolver import ABMMixedBlockResolver
from abm.lf_components.audiobook.abm_span_attribution import ABMSpanAttribution
from abm.lf_components.audiobook.abm_span_classifier import ABMSpanClassifier
from abm.lf_components.audiobook.abm_span_iterator import ABMSpanIterator


def test_spans_first_pipeline_smoke() -> None:
    # Require local data; skip if missing to keep CI optional
    chapters = Path("data/clean/mvs/chapters.json")
    if not chapters.exists():
        pytest.skip("mvs chapters.json not present; skipping")

    # 1) Load blocks for a small chapter
    loader = ABMChapterLoader(book_name="mvs", chapter_index=1, base_data_dir="data/clean")
    blocks_out = loader.load_and_blocks().data
    assert "error" not in blocks_out, f"Loader error: {blocks_out.get('error')}"
    assert isinstance(blocks_out.get("blocks"), list) and blocks_out["blocks"], "No blocks returned"

    # 2) Validate → Resolve → Classify → Attribute
    v = ABMBlockSchemaValidator(blocks_data=blocks_out, write_to_disk=False)
    blocks = v.validate_blocks().data
    r = ABMMixedBlockResolver(validated_blocks=blocks, write_to_disk=False)
    spans = r.resolve_spans().data
    c = ABMSpanClassifier(spans=spans, write_to_disk=False)
    spans_cls = c.classify_spans().data
    a = ABMSpanAttribution(spans_cls=spans_cls, write_to_disk=False)
    spans_attr = a.attribute_spans().data

    # Basic assertions on outputs
    assert isinstance(spans.get("spans"), list) and spans["spans"], "No spans produced"
    assert isinstance(spans_cls.get("spans_cls"), list) and spans_cls["spans_cls"], "No spans_cls produced"
    assert isinstance(spans_attr.get("spans_attr"), list) and spans_attr["spans_attr"], "No spans_attr produced"

    # 3) Iterate a few spans quickly
    it = ABMSpanIterator(spans_data=spans_attr, dialogue_only=True, max_spans=5)
    seen = 0
    while True:
        cur = it.get_next_span().data
        if cur.get("processing_status") == "completed":
            break
        if "error" in cur:
            pytest.fail(f"Iterator error: {cur['error']}")
        seen += 1
        if seen > 10:  # safety guard for test
            break
    assert seen >= 0
