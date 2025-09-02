from abm.lf_components.audiobook.deterministic_confidence import (
    DeterministicConfidenceConfig,
    DeterministicConfidenceScorer,
)


def test_dialogue_tag_high_confidence() -> None:
    scorer = DeterministicConfidenceScorer(DeterministicConfidenceConfig())
    conf, evidence, method = scorer.score(
        dialogue_text='"Hello"',
        before_text=None,
        after_text="Bob said.",
        detected_method="dialogue_tag",
        detected_speaker="Bob",
        prev_dialogue_speaker=None,
    )
    assert 0.7 <= conf <= 0.95
    assert evidence["confidence_method"] == "deterministic_v1"
    assert method == "deterministic_v1"


def test_continuity_boost() -> None:
    scorer = DeterministicConfidenceScorer(DeterministicConfidenceConfig())
    conf1, _, _ = scorer.score(
        dialogue_text='"Hi"',
        before_text=None,
        after_text="Alice said.",
        detected_method="dialogue_tag",
        detected_speaker="Alice",
        prev_dialogue_speaker=None,
    )
    conf2, _, _ = scorer.score(
        dialogue_text='"Again"',
        before_text=None,
        after_text=None,
        detected_method="proper_noun_proximity",
        detected_speaker="Alice",
        prev_dialogue_speaker="Alice",
    )
    assert conf2 >= conf1 - 0.05  # continuity should not drop drastically
