"""Hit blank-line branch in TOC entry parsing to complete coverage."""

from abm.classifier import classify_sections
from abm.classifier.types import Page


def test_toc_parsing_skips_blank_lines():
    p = Page(
        page_index=5,
        lines=["Contents", "", "Introduction .... 1"],
    )
    out = classify_sections({"pages": [p]})
    entries = out["toc"]["entries"]
    # Parsing should still succeed despite the blank line
    assert any(
        e["title"].lower() == "introduction" and e["page"] == 1
        for e in entries
    )
