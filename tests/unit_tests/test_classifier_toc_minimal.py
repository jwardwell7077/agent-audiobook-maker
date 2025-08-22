"""Minimal tests for TOC detection and parsing in the classifier.

These aim to hit key branches while staying simple.
"""

from abm.classifier import classify_sections
from abm.classifier.types import Page


def make_pages_case_valid() -> list[Page]:
    # Page 1: page-number-only + some front text
    # includes an inline trailing number token to strip ("--- 12")
    p1 = Page(page_index=1, lines=["1", "Preface text", "--- 12"]) 

    # Page 2: TOC with heading and two valid entries
    p2 = Page(
        page_index=2,
        lines=[
            "Table of Contents",
            "Introduction ........ 1",
            "Chapter 1 ........ 7",
        ],
    )

    # Page 3: body sample with an inline trailing number to strip
    p3 = Page(page_index=7, lines=["Some paragraph that ends with 44"])

    # Page 4: roman numeral only to test roman marker
    p4 = Page(page_index=8, lines=["iv", "Another paragraph."])

    return [p1, p2, p3, p4]


def test_minimal_toc_parsing_and_markers():
    inputs = {"pages": make_pages_case_valid()}
    out = classify_sections(inputs)

    # TOC parsed entries
    entries = out["toc"]["entries"]
    assert len(entries) >= 2
    assert entries[0]["title"].lower() == "introduction"
    assert entries[0]["page"] == 1
    assert entries[1]["title"].lower().startswith("chapter 1")
    assert entries[1]["page"] == 7

    # toc span should be non-empty and within total text length
    toc_span = out["toc"]["span"]
    assert isinstance(toc_span, list) and len(toc_span) == 2
    assert 0 <= toc_span[0] <= toc_span[1]

    # page markers include numeric (1, 12, 44) and roman (IV)
    markers = out["front_matter"]["document_meta"]["page_markers"]
    values = {m["value"] for m in markers}
    assert "1" in values and "44" in values
    assert "IV" in values

    # sections spans are monotonically increasing
    fspan = out["front_matter"]["span"]
    bspan = out["chapters_section"]["span"]
    bkspan = out["back_matter"]["span"]
    assert fspan[0] <= fspan[1] <= bspan[0]
    assert bspan[0] <= bspan[1] <= bkspan[0]
    assert bkspan[0] <= bkspan[1]


def test_toc_detected_but_no_entries():
    # TOC heading present, but lines are unparseable as entries
    p1 = Page(
        page_index=1,
        lines=["Table of Contents", "A heading", "Some intro text"],
    )
    p2 = Page(page_index=2, lines=["Body text without numbers"])

    out = classify_sections({"pages": [p1, p2]})

    assert out["toc"]["entries"] == []
    assert "no toc entries parsed" in out["toc"]["warnings"]
