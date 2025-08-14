from pipeline.ingestion.parsers.structured_toc import parse_structured_toc


def run_parse(text: str):  # small helper
    return parse_structured_toc(text)


def test_structured_success():
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


def test_structured_failure_when_missing():
    # only one chapter => should fail (return None)
    text = (
        "Chapter 1: Lone Chapter\n"
        "Some text but no second chapter."
    )
    parsed = run_parse(text)
    assert parsed is None
