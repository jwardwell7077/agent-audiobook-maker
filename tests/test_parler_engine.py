import numpy as np
import pytest

from abm.voice.engines.parler_engine import ParlerEngine


@pytest.mark.slow
def test_parler_engine_smoke():
    engine = ParlerEngine()
    y = engine.synthesize(
        "Hello there.",
        "Rebecca",
        description="Rebecca's voice is neutral, warm and steady, unhurried pacing, close-mic studio, very clear audio.",
        seed=1,
    )
    assert engine.target_sr == 48000
    assert y.dtype == np.float32
    assert y.ndim == 1 and y.shape[0] > 0
    assert not np.isnan(y).any()

    z = engine.synthesize(
        "Testing again.",
        "Will",
        description="Will's voice is youthful baritone with a calm, earnest tone, medium pace, very clear audio.",
        seed=2,
    )
    assert z.dtype == np.float32
    assert z.ndim == 1 and z.shape[0] > 0
    assert not np.isnan(z).any()
