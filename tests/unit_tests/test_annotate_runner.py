"""Tests for AnnotateRunner and attribute utilities."""

from abm.annotate.annotate_cli import AnnotateRunner
from abm.annotate.segment import Span as SegSpan
from abm.annotate.segment import SpanType as SegSpanType


def _make_doc() -> dict:
    return {
        "chapters": [
            {
                "chapter_index": 0,
                "title": "Ch1",
                "paragraphs": [
                    "Chapter 1: Start",
                    "<User: Quinn>",
                    '"Hello," said Bob.',
                    "Author's note here",
                    "***",
                    "It was late.",
                ],
            }
        ]
    }


def test_runner_run_basic() -> None:
    runner = AnnotateRunner()
    doc = _make_doc()
    out = runner.run(doc)
    chapter = out["chapters"][0]
    assert isinstance(chapter["roster"], dict)
    assert any(s["type"] == "Dialogue" for s in chapter["spans"])


def test_runner_run_only_indices_skips() -> None:
    runner = AnnotateRunner()
    doc = _make_doc()
    out = runner.run(doc, only_indices=[99])
    ch = out["chapters"][0]
    assert "spans" not in ch


def test_attribute_single_branches() -> None:
    runner = AnnotateRunner()
    full_text = "Test"
    roster = {}
    # Meta
    meta_span = SegSpan(0, 1, SegSpanType.META, "", 0)
    assert runner._attribute_single(full_text, meta_span, roster) == (
        "Narrator",
        "rule:non_story",
        1.0,
    )
    # Section break
    sb_span = SegSpan(0, 1, SegSpanType.SECTION_BREAK, "", 0)
    assert runner._attribute_single(full_text, sb_span, roster)[1] == "rule:non_story"
    # Heading
    head_span = SegSpan(0, 1, SegSpanType.HEADING, "", 0)
    assert runner._attribute_single(full_text, head_span, roster)[1] == "rule:non_story"
    # System line
    sys_line = SegSpan(0, 1, SegSpanType.SYSTEM, "", 0, subtype="LineAngle")
    assert runner._attribute_single(full_text, sys_line, roster) == (
        "System",
        "rule:system_line",
        1.0,
    )
    # System inline
    sys_inline = SegSpan(0, 1, SegSpanType.SYSTEM, "", 0, subtype="InlineAngle")
    assert runner._attribute_single(full_text, sys_inline, roster)[1] == "rule:system_inline"
    # Narration
    narr = SegSpan(0, 1, SegSpanType.NARRATION, "", 0)
    assert runner._attribute_single(full_text, narr, roster)[0] == "Narrator"
    # Dialogue
    dial = SegSpan(0, 1, SegSpanType.DIALOGUE, "", 0)
    assert runner._attribute_single(full_text, dial, roster)[1] == "rule:placeholder"
