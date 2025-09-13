"""Tests for the review markdown generator."""

from abm.annotate.review import make_review_markdown


def test_make_review_markdown_produces_sections() -> None:
    chapters = [
        {
            "chapter_index": 0,
            "title": "Ch 1",
            "display_title": "Ch 1",
            "normalize_report": {"is_heading": False, "counts": {}},
            "spans": [
                {
                    "id": 1,
                    "type": "Dialogue",
                    "speaker": "Alice",
                    "confidence": 0.9,
                    "method": "manual",
                    "text": "Hello",
                },
                {
                    "id": 2,
                    "type": "Narration",
                    "speaker": "Unknown",
                    "confidence": 0.2,
                    "method": "rule",
                    "text": "Mystery",
                },
            ],
        }
    ]

    md = make_review_markdown(chapters)

    assert "## All spans" in md
    assert "## Method breakdown" in md
    assert "| 0 | 1 | Dialogue | Alice" in md
    assert "| manual | 1 |" in md
