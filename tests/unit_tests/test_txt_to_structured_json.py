from __future__ import annotations

from pathlib import Path

from abm.ingestion.txt_to_structured_json import (
    TxtToStructuredOptions,
    convert_txt_to_structured,
    parse_paragraphs,
)


def test_parse_paragraphs_basic() -> None:
    text = "Line 1\n\nLine 2"
    assert parse_paragraphs(text) == ["Line 1", "Line 2"]


def test_parse_paragraphs_multiple_blank_lines() -> None:
    text = "A\n\n\n\nB"
    assert parse_paragraphs(text) == ["A", "B"]


def test_parse_paragraphs_preserve_lines_inside_paragraph() -> None:
    text = "A1\nA2\n\nB1\nB2"
    assert parse_paragraphs(text) == ["A1\nA2", "B1\nB2"]


def test_parse_paragraphs_crlf_normalization() -> None:
    text = "A1\r\nA2\r\n\r\nB1\r\nB2\r\n"
    assert parse_paragraphs(text) == ["A1\nA2", "B1\nB2"]


def test_convert_txt_to_structured(tmp_path: Path) -> None:
    p = tmp_path / "sample.txt"
    p.write_text("A1\nA2\n\nB1\nB2\n", encoding="utf-8")
    obj = convert_txt_to_structured(
        p,
        TxtToStructuredOptions(book_id="BOOK", chapter_id="BOOK_CH0001", chapter_index=1, title="Ch 1"),
    )
    assert obj["paragraphs"] == ["A1\nA2", "B1\nB2"]
    assert isinstance(obj["text"], str) and obj["text"].startswith("A1\nA2\n\nB1\nB2")

    assert obj["book_id"] == "BOOK"
    assert obj["chapter_id"] == "BOOK_CH0001"
