"""Tests for extracting LLM candidates from annotated chapters."""

from abm.annotate.llm_prep import LLMCandidateConfig, LLMCandidatePreparer


def test_prepare_selects_low_confidence_and_unknown() -> None:
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
                        "method": "rule:unknown",
                        "confidence": 0.5,
                    },
                    {
                        "id": 2,
                        "type": "Thought",
                        "speaker": "Alice",
                        "start": 6,
                        "end": 11,
                        "text": "world",
                        "method": "rule:coref",
                        "confidence": 0.95,
                    },
                    {
                        "id": 3,
                        "type": "Dialogue",
                        "speaker": "Bob",
                        "start": 12,
                        "end": 16,
                        "text": "nope",
                        "method": "rule:direct",
                        "confidence": 0.99,
                    },
                ],
            }
        ]
    }

    prep = LLMCandidatePreparer(LLMCandidateConfig())
    cands = prep.prepare(chapters)

    assert {c.span_id for c in cands} == {1, 2}
    assert all(c.fingerprint for c in cands)
    assert cands[0].roster == ["Alice", "Bob"]

