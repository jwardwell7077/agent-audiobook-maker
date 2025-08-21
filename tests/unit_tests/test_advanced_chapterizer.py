"""Unit tests for advanced chapterizer logic.

Tests chapter extraction from TOC and error handling for missing TOC marker.
"""

import pytest

from pipeline.ingestion.advanced_chapterizer import (
    attempt_advanced_chapterize,
)


def test_advanced_chapterize_success() -> None:
    text = (
        "Table of Contents\n"
        "• Chapter 1: One\n"
        "• Chapter 2: Two\n\n"
        "Chapter 1: One\nThis is first chapter. It has two sentences.\n\n"
        "Chapter 2: Two\n"
        "Second chapter here! More words."
    )
    chapters = attempt_advanced_chapterize("bk", text, pages=[text], min_chapters=2)
    assert len(chapters) == 2
    assert chapters[0].title == "One"
    assert chapters[0].meta["word_count"] > 0
    assert chapters[1].meta["chapter_number"] == 2


def test_advanced_chapterize_failure_missing_toc() -> None:
    text = "Chapter 1: Start\nHello world"
    # Expect explicit failure due to missing Table of Contents marker
    with pytest.raises(ValueError, match="Table of Contents"):
        attempt_advanced_chapterize("bk", text, pages=[text], min_chapters=1)
