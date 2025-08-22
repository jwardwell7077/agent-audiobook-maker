"""Extra coverage tests to exercise branchy paths in the classifier."""

from abm.classifier import classify_sections
from abm.classifier.types import Page


def test_empty_input_spans_and_no_toc():
    out = classify_sections({"pages": []})
    assert out["toc"]["entries"] == []
    assert out["front_matter"]["span"] == [0, 0]
    assert out["chapters_section"]["span"] == [0, 0]
    assert out["back_matter"]["span"] == [0, 0]


def test_toc_heuristic_detection_no_heading():
    # No explicit heading, but 3+ dotted lines with ending numbers
    # triggers heuristics
    p1 = Page(
        page_index=10,
        lines=[
            "Intro ........ 3",
            "Chapter 1 ........ 7",
            "Chapter 2 ........ 21",
        ],
    )
    out = classify_sections({"pages": [p1]})
    assert len(out["toc"]["entries"]) >= 3
    assert out["toc"]["span"][1] >= out["toc"]["span"][0]


def test_non_toc_page_long_line_is_ignored_in_heuristics():
    # A non-TOC page with a very long line should not inflate candidate ratio
    long_line = "x" * 200
    p1 = Page(page_index=1, lines=[long_line, "Regular paragraph."])
    out = classify_sections({"pages": [p1]})
    # No TOC found
    assert out["toc"]["entries"] == []
    assert out["toc"]["warnings"][0] == "no toc entries parsed"
