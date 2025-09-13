from abm.audio.text_normalizer import Chunker, TextNormalizer


def test_normalize_game_tokens():
    text = "He gained <HP 10/10> and 5 exp. <Skills> “Ok… let's go.”"
    result = TextNormalizer.normalize(text)
    assert (
        result
        == 'He gained HP ten out of ten and five experience. Skills "Ok... let\'s go."'
    )


def test_chunker_respects_quotes_and_caps():
    text = 'He said "Hello. Again." Then he left.'
    parts = Chunker.split(text, engine="piper", max_chars=30)
    assert parts == ['He said "Hello. Again."', "Then he left."]


def test_chunker_handles_ellipsis():
    text = "Wait... really? Yes!"
    parts = Chunker.split(text, engine="xtts", max_chars=15)
    assert parts == ["Wait... really?", "Yes!"]


def test_chunker_hard_wrap_long_sentence():
    long_sentence = " ".join(["word"] * 40)
    parts = Chunker.split(long_sentence, engine="piper", max_chars=50)
    assert all(len(p) <= 50 for p in parts)
    assert " ".join(parts) == long_sentence
