import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("torch")
pytest.importorskip("torchaudio")
pytest.importorskip("transformers")
pytest.importorskip("parler_tts")

from abm.voice.engines import ParlerEngine


@pytest.mark.slow
def test_parler_audio_invariants():
    eng = ParlerEngine()
    y = eng.synthesize_to_array(
        "Hello there.",
        "Rebecca",
        description="Rebecca's voice is neutral, warm and steady, unhurried pacing, close-mic studio, very clear audio.",
        seed=1,
    )
    assert eng.target_sr == 48000
    assert y.dtype == np.float32
    assert y.ndim == 1 and y.size > 0
    assert not np.isnan(y).any()


@pytest.mark.slow
def test_parler_determinism_with_seed():
    eng = ParlerEngine()
    params = dict(
        text="Testing determinism.",
        voice_id="Will",
        description="Will's voice is youthful baritone with a calm, earnest tone, medium pace, very clear audio.",
        seed=123,
    )
    a = eng.synthesize_to_array(**params)
    b = eng.synthesize_to_array(**params)
    assert np.array_equal(a, b)


@pytest.mark.slow
def test_parler_two_voices_distinct():
    eng = ParlerEngine()
    text = "Checking distinct voices."
    rebecca = eng.synthesize_to_array(
        text,
        "Rebecca",
        description="Rebecca's voice is neutral, warm and steady, unhurried pacing, close-mic studio, very clear audio.",
        seed=111,
    )
    will = eng.synthesize_to_array(
        text,
        "Will",
        description="Will's voice is youthful baritone with a calm, earnest tone, medium pace, very clear audio.",
        seed=222,
    )
    assert not np.array_equal(rebecca, will)
