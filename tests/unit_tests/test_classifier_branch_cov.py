import pytest

pytest.skip(
    "Legacy page-based classifier tests are deprecated. The classifier is now JSONL-first and block-based."
    " See docs/INGESTION_PIPELINE_V2.md and SECTION_CLASSIFIER_SPEC.md.",
    allow_module_level=True,
)
