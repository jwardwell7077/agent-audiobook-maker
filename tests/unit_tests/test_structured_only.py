"""Unit tests for structured TOC parsing helper.

Focus: ensure happy path parses two chapters and failure path returns None.
"""

from typing import Any, TypedDict

from pipeline.ingestion.parsers.structured_toc import parse_structured_toc


class _ParsedChapters(TypedDict):
    chapters: list[dict[str, Any]]


def run_parse(text: str) -> _ParsedChapters | None:
    """Parse text via structured TOC parser returning payload or None."""
    return parse_structured_toc(text)  # type: ignore[return-value]


def test_structured_success() -> None:
    """Structured parser returns chapter list for valid TOC + headings."""
    text = (
        "Intro stuff here.\n\nTable of Contents\n"
        "• Chapter 1: One\n"
        "• Chapter 2: Two\n\n"
        "Chapter 1: One\nBody one.\n\n"
        "Chapter 2: Two\nBody two."
    )
    parsed = run_parse(text)
    assert parsed is not None
    assert len(parsed["chapters"]) == 2
    assert parsed["chapters"][0]["number"] == 1


def test_structured_failure_when_missing() -> None:
    """Return None when insufficient chapters present (confidence fail)."""
    # only one chapter => should fail (return None)
    text = "Chapter 1: Lone Chapter\nSome text but no second chapter."
    parsed = run_parse(text)
    assert parsed is None
