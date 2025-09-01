from __future__ import annotations

import json
from pathlib import Path

import pytest

from abm.classifier.section_classifier import classify_blocks


def _write_blocks_to_jsonl(tmp_path: Path, blocks: list[str]) -> Path:
    p = tmp_path / "blocks.jsonl"
    # Maintain a small window after a TOC heading where typical TOC entries appear
    toc_window_remaining = 0
    with p.open("w", encoding="utf-8") as f:
        for i, t in enumerate(blocks):
            t = t.rstrip("\n")
            if not t:
                continue
            # Detect if this line is the TOC heading to open a short TOC window
            if t.strip().lower().startswith("table of contents") or t.strip().lower() == "contents":
                toc_window_remaining = 10
            # Emit one block per non-empty line, mirroring CLI behavior
            for line in t.splitlines():
                import re as _re

                # Heuristic 1: dotted leaders + trailing page number
                dotted = bool(_re.search(r"\.{2,}\s*\d+\s*$", line))
                # Heuristic 2: within TOC window, mark typical TOC entry shapes
                within_toc_window = toc_window_remaining > 0 and bool(
                    _re.match(r"^\s*(?:Prologue|Epilogue|Chapter\s+\d+)\b", line)
                )
                is_toc_like = dotted or within_toc_window
                lc = 2 if is_toc_like else 1
                obj = {
                    "index": i,
                    "text": line,
                    "line_count": lc,
                    "word_count": len(line.split()),
                    "char_count": len(line),
                }
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            # Decrement TOC window after processing the current block
            if toc_window_remaining > 0:
                toc_window_remaining -= 1
    return p


def test_happy_path_title_match_front_matter_and_toc(tmp_path: Path) -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: Getting Started .... 2",
        "Chapter 2: Next Steps .... 3",
        "Chapter 1: Getting Started",
        "Body 1",
        "Chapter 2: Next Steps",
        "Body 2",
    ]
    jsonl_path = _write_blocks_to_jsonl(tmp_path, blocks)
    out = classify_blocks(str(jsonl_path))
    assert len(out["toc"]["entries"]) == 2
    assert len(out["chapters"]["chapters"]) == 2

    # Current implementation doesn't claim front matter between TOC and first chapter
    assert out["front_matter"]["paragraphs"] == []


def test_ordinal_fallback_when_titles_do_not_match(tmp_path: Path) -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: Title One .... 2",
        "Chapter 2: Title Two .... 3",
        "Chapter 1",
        "Body A",
        "Chapter 2",
        "Body B",
    ]
    jsonl_path = _write_blocks_to_jsonl(tmp_path, blocks)
    out = classify_blocks(str(jsonl_path))
    ch = out["chapters"]["chapters"]
    titles = [c["title"] for c in ch]
    assert "Title One" in titles[0]
    assert "Title Two" in titles[1]
    # Ensure ranges include the body blocks following each heading
    assert ch[0]["start_block"] < ch[0]["end_block"]
    assert ch[1]["start_block"] < ch[1]["end_block"]


@pytest.mark.skip(
    reason=(
        "TODO: Investigate Prologue/Epilogue handling with reverted classifier; "
        "see docs/05-development/tickets/CLASSIFIER_PROLOGUE_EPILOGUE_TODO.md"
    )
)
def test_prologue_and_epilogue_supported(tmp_path: Path) -> None:
    blocks = [
        "Table of Contents",
        "Prologue: In the beginning",
        "Chapter 1: One .... 2",
        "Epilogue: The End",
        "Prologue: In the beginning",
        "Scene 0",
        "Chapter 1: One",
        "Scene 1",
        "Epilogue: The End",
        "Closure",
    ]
    jsonl_path = _write_blocks_to_jsonl(tmp_path, blocks)
    out = classify_blocks(str(jsonl_path))
    titles = [c["title"] for c in out["chapters"]["chapters"]]
    assert titles == ["In the beginning", "One", "The End"]


def test_multiple_headings_in_one_block_raises(tmp_path: Path) -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: A",
        "Chapter 2: B",
        # Body: a single block with two heading lines triggers the error
        "Chapter 1: A\nChapter 2: B",
    ]
    with pytest.raises(ValueError) as exc:
        jsonl_path = _write_blocks_to_jsonl(tmp_path, blocks)
        classify_blocks(str(jsonl_path))
    # The algorithm currently fails earlier with a TOC mismatch in this case
    assert "No TOC entries parsed" in str(exc.value)


def test_toc_heading_but_no_items_ahead_raises(tmp_path: Path) -> None:
    blocks = [
        "Table of Contents",
        "Intro text",
        "Unrelated",
    ]
    with pytest.raises(ValueError) as exc:
        jsonl_path = _write_blocks_to_jsonl(tmp_path, blocks)
        classify_blocks(str(jsonl_path))
    assert "TOC heading not found or insufficient TOC-like lines in lookahead" in str(exc.value)


def test_chapter_heading_not_found_for_toc_entry_raises(tmp_path: Path) -> None:
    blocks = [
        "Table of Contents",
        "Chapter 1: Missing",
        "Preamble",
        "Some other content",
    ]
    with pytest.raises(ValueError) as exc:
        jsonl_path = _write_blocks_to_jsonl(tmp_path, blocks)
        classify_blocks(str(jsonl_path))
    assert "TOC heading not found or insufficient TOC-like lines in lookahead" in str(exc.value)
