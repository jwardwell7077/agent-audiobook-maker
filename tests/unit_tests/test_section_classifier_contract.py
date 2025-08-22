"""
Minimal scaffolding tests for Section Classifier contracts.
These are intentionally skipped until implementation is started.
Refer to docs/SECTION_CLASSIFIER_SPEC.md and
the JSON Schemas in docs/schemas/classifier/.
"""

import pytest


@pytest.mark.skip(reason="Classifier not implemented yet")
def test_classifier_outputs_four_json_artifacts():
    # Contract:
    # - front_matter.json
    # - toc.json
    # - chapters_section.json
    # - back_matter.json
    # See schemas and examples under docs/.
    assert True


@pytest.mark.skip(reason="Classifier not implemented yet")
def test_page_number_only_lines_removed_and_inline_tokens_warned():
    # Contract: page-number-only lines removed from body;
    # inline tokens stripped with warning.
    assert True
