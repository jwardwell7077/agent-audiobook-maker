import numpy as np
import numpy as np
import pytest

from abm.voice.engines import ParlerEngine


@pytest.mark.slow
def test_parler_audio_invariants():
    eng = ParlerEngine()
    y = eng.synthesize(
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
    a = eng.synthesize(**params)
    b = eng.synthesize(**params)
    assert np.array_equal(a, b)
