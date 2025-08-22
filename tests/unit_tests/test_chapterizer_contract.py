"""
Minimal scaffolding tests for Chapterizer contracts.
These are intentionally skipped until implementation is started.
Refer to docs/CHAPTERIZER_SPEC.md.
"""

import pytest


@pytest.mark.skip(reason="Chapterizer not implemented yet")
def test_toc_titles_anchor_chapters_with_thresholds():
    # Contract: Use TOC titles to anchor chapters.
    # Abort if >5 duplicate titles; abort if >40% unmatched titles.
    assert True


@pytest.mark.skip(reason="Chapterizer not implemented yet")
def test_fallback_numeric_patterns_when_no_toc():
    # Contract: fallback to numeric patterns (Chapter N, Roman numerals),
    # anchored to lines where the title is the sole entity on the line.
    assert True
