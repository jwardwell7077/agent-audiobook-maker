from __future__ import annotations

from abm.ingestion.raw_to_welldone import RawToWellDone, WellDoneOptions


def test_process_text_defaults_reflow_and_dehyphenate() -> None:
    text = "Para one line\nwrap-\nup.\n\nSecond  para   with  gaps.\n"
    out = RawToWellDone().process_text(text, WellDoneOptions())
    # Reflowed single paragraph lines and dehyphenated
    assert "wrapup." in out
    # Double spaces deduped by default
    assert "para with gaps." in out
    # Paragraph separation preserved (blank line between)
    assert "\n\n" in out


def test_split_each_line_creates_paragraphs_per_line() -> None:
    text = "A\nB\n\nC"
    out = RawToWellDone().process_text(text, WellDoneOptions(split_each_line=True, reflow_paragraphs=False))
    parts = [p for p in out.split("\n\n") if p]
    assert parts == ["A", "B", "C"]


def test_split_headings_promotes_heading_lines() -> None:
    text = "Intro line\nChapter 1: Start\nFollow up line\n\nEpilogue\nTail"
    out = RawToWellDone().process_text(text, WellDoneOptions(split_headings=True, reflow_paragraphs=False))
    paras = [p.strip() for p in out.split("\n\n") if p.strip()]
    # Heading lines should be their own paragraphs
    assert "Chapter 1: Start" in paras
    assert "Epilogue" in paras


def test_bulleted_toc_splits_into_items() -> None:
    text = "• Intro\n• Chap 1\n• Chap 2\n• Chap 3"
    out = RawToWellDone().process_text(text, WellDoneOptions())
    paras = [p for p in out.split("\n\n") if p]
    # When 3+ bullets, each becomes its own paragraph
    assert len(paras) >= 3 and all(p.startswith("• ") for p in paras)


def test_no_dehyphenation_and_no_reflow_preserves_breaks() -> None:
    text = "wrap-\nping example"
    out = RawToWellDone().process_text(
        text,
        WellDoneOptions(reflow_paragraphs=False, dehyphenate_wraps=False, dedupe_inline_spaces=False),
    )
    assert "-\n" in out  # hyphenation preserved


def test_split_headings_single_line_paragraph_unchanged() -> None:
    # Single-line paragraphs should bypass split_headings splitting path
    text = "Prologue"
    out = RawToWellDone().process_text(text, WellDoneOptions(split_headings=True, reflow_paragraphs=False))
    assert out.strip() == "Prologue"


def test_strip_trailing_spaces_disabled_keeps_spaces() -> None:
    text = "A  \nB  "
    out = RawToWellDone().process_text(
        text,
        WellDoneOptions(
            strip_trailing_spaces=False,
            reflow_paragraphs=False,
            dedupe_inline_spaces=False,
        ),
    )
    # Because we didn't strip trailing spaces and didn't reflow, spaces at line ends persist
    assert out.splitlines()[0].endswith("  ")
