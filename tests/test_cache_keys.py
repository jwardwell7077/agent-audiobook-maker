from pathlib import Path

from abm.voice.cache import cache_path, make_cache_key


def test_cache_key_stability(tmp_path: Path) -> None:
    payload = {
        "engine": "piper",
        "voice": "en_US",
        "text": "hello",
        "style": {"pace": 1.0},
        "sr": 48000,
    }
    k1 = make_cache_key(payload)
    k2 = make_cache_key(payload)
    assert k1 == k2
    k3 = make_cache_key({**payload, "style": {"pace": 0.9}})
    assert k1 != k3
    p = cache_path(tmp_path, "piper", "en_US", k1)
    assert p == tmp_path / "piper" / "en_US" / f"{k1}.wav"
