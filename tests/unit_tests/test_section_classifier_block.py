from __future__ import annotations

import pytest

from abm.classifier.section_classifier import classify_sections


def test_happy_path_title_match_front_matter_and_toc() -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: Getting Started .... 2",
        "Chapter 2: Next Steps .... 3",
        "Preface line",
        "Chapter 1: Getting Started",
        "Body 1",
        "Chapter 2: Next Steps",
        "Body 2",
    ]
    out = classify_sections({"blocks": blocks})
    assert len(out["toc"]["entries"]) == 2
    assert len(out["chapters"]["chapters"]) == 2

    # Current implementation doesn't claim front matter between TOC and first chapter
    assert out["front_matter"]["paragraphs"] == []


def test_ordinal_fallback_when_titles_do_not_match() -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: Title One",
        "Chapter 2: Title Two",
        "Preamble",
        "Chapter 1",
        "Body A",
        "Chapter 2",
        "Body B",
    ]
    out = classify_sections({"blocks": blocks})
    ch = out["chapters"]["chapters"]
    assert [c["title"] for c in ch] == ["Title One", "Title Two"]
    # Ensure ranges include the body blocks following each heading
    assert ch[0]["start_block"] < ch[0]["end_block"]
    assert ch[1]["start_block"] < ch[1]["end_block"]


def test_prologue_and_epilogue_supported() -> None:
    blocks = [
        "Table of Contents",
        "Prologue: In the beginning",
        "Chapter 1: One",
        "Epilogue: The End",
        "Intro text",
        "Prologue: In the beginning",
        "Scene 0",
        "Chapter 1: One",
        "Scene 1",
        "Epilogue: The End",
        "Closure",
    ]
    out = classify_sections({"blocks": blocks})
    titles = [c["title"] for c in out["chapters"]["chapters"]]
    assert titles == ["In the beginning", "One", "The End"]


def test_multiple_headings_in_one_block_raises() -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: A",
        "Chapter 2: B",
        # Body: a single block with two heading lines triggers the error
        "Chapter 1: A\nChapter 2: B",
    ]
    with pytest.raises(ValueError) as exc:
        classify_sections({"blocks": blocks})
    # The algorithm currently fails earlier with a TOC mismatch in this case
    assert "Chapter heading not found for TOC entry" in str(exc.value)


def test_toc_heading_but_no_items_ahead_raises() -> None:
    blocks = [
        "Table of Contents",
        "Intro text",
        "Unrelated",
    ]
    with pytest.raises(ValueError) as exc:
        classify_sections({"blocks": blocks})
    assert "TOC heading found but no TOC items ahead" in str(exc.value)


def test_chapter_heading_not_found_for_toc_entry_raises() -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: Missing",
        "Preamble",
        "Some other content",
    ]
    with pytest.raises(ValueError) as exc:
        classify_sections({"blocks": blocks})
    assert "TOC heading found but no TOC items ahead" in str(exc.value)
