"""Target branch points to reach 100% coverage for current slice."""

from abm.classifier import classify_sections
from abm.classifier.types import Page


def test_toc_pages_detected_but_no_overlap_with_page_spans():
    # Page 1: normal body line ensures page_spans has key 1
    p1 = Page(page_index=1, lines=["Intro text"])
    # Page 2: heuristic-detected TOC due to 3 lines ending with numbers,
    # but all are page-number-only and removed, so no page_spans entry for 2
    p2 = Page(page_index=2, lines=["1", "2", "3"])
    out = classify_sections({"pages": [p1, p2]})
    # toc_pages present, page_spans present, but common is empty
    # => span remains [0,0]
    assert out["toc"]["span"] == [0, 0]
    assert out["toc"]["entries"] == []
    assert "no toc entries parsed" in out["toc"]["warnings"]


def test_parse_toc_rejects_digit_only_title():
    # A line like "123 ..... 7" should not create an entry because
    # title is digits only
    # digit-only title rejected
    p1 = Page(page_index=1, lines=["Contents", "123 ..... 7"])
    out = classify_sections({"pages": [p1]})
    assert out["toc"]["entries"] == []
