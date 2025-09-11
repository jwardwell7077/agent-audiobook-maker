from abm.annotate import ChapterNormalizer, Segmenter, SpanType


def test_segmenter_basic_spans() -> None:
    chapter = {
        "title": "Test",
        "paragraphs": [
            "Chapter 1: Start",
            "You gained <Skill>!",
            "He said, \"Hello.\"",
            "She thought, 'Hmm.'",
            "***",
            "<Status>.",
            "Support me on Patreon",
        ],
    }

    normalizer = ChapterNormalizer()
    normalized = normalizer.normalize(chapter)

    segmenter = Segmenter()
    spans = segmenter.segment(normalized)

    span_types = {s.type for s in spans}
    assert SpanType.HEADING in span_types
    assert SpanType.META in span_types
    assert SpanType.SECTION_BREAK in span_types
    assert SpanType.SYSTEM in span_types
    assert SpanType.DIALOGUE in span_types
    assert SpanType.THOUGHT in span_types

    inline_span = next(s for s in spans if s.subtype == "InlineAngle")
    assert inline_span.text == "<Skill>"

    line_span = next(s for s in spans if s.subtype == "LineAngle")
    assert line_span.text.startswith("<Status>")
