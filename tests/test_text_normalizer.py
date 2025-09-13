import pytest

from abm.audio.text_normalizer import Chunker, TextNormalizer


def test_normalizer_exp_and_stats_and_brackets():
    s = "He saw <HP 10/10> and gained 5 exp. Then went to <Shop>."
    n = TextNormalizer.normalize(s)
    assert "HP ten out of ten" in n
    assert "five experience" in n
    assert "<" not in n and ">" not in n


def test_chunker_caps_and_boundaries():
    txt = 'One sentence. Another one here! "Quoted start." Final?'
    chunks = Chunker.split(txt, engine="piper", max_chars=20)
    assert all(len(c) <= 20 for c in chunks)
    # Should not return empty chunks
    assert all(c.strip() for c in chunks)


@pytest.mark.parametrize(
    "txt,expected",
    [
        ("Dr. Smith waved. 'Hello.'", ["Dr. Smith waved.", "'Hello.'"]),
        ('He paused... "Okay."', ["He paused...", '"Okay."']),
    ],
)
def test_chunker_edge_cases(txt, expected):
    chunks = Chunker.split(txt, engine="piper", max_chars=18)
    assert chunks == expected
