"""Tests for extracting LLM candidates from annotated chapters."""

from abm.annotate.llm_prep import LLMCandidateConfig, LLMCandidatePreparer


def test_prepare_selects_low_confidence_and_unknown() -> None:
    """Ensure preparer finds Unknown or low-confidence spans."""
    chapters = {
        "chapters": [
            {
                "chapter_index": 0,
                "title": "Ch1",
                "text": "Hello world",
                "roster": {"Alice": ["Alice"], "Bob": ["Bob"]},
                "spans": [
                    {
                        "id": 1,
                        "type": "Dialogue",
                        "speaker": "Unknown",
                        "start": 0,
                        "end": 5,
                        "text": "Hello",
                        "confidence": 0.5,
                    },
                    {
                        "id": 2,
                        "type": "Thought",
                        "speaker": "Alice",
                        "start": 6,
                        "end": 11,
                        "text": "world",
                        "confidence": 0.85,
                    },
                    {
                        "id": 3,
                        "type": "Dialogue",
                        "speaker": "Bob",
                        "start": 12,
                        "end": 16,
                        "text": "nope",
                        "confidence": 0.99,
                    },
                ],
            }
        ]
    }

    prep = LLMCandidatePreparer(LLMCandidateConfig())
    cands = prep.prepare(chapters)

    assert len(cands) == 2
    spans = {(c["start"], c["end"]) for c in cands}
    assert spans == {(0, 5), (6, 11)}
    assert cands[0]["roster"] == {"Alice": ["Alice"], "Bob": ["Bob"]}

