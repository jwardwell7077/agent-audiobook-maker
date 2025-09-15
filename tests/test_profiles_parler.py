from pathlib import Path

from abm.profiles import load_profiles


def test_parler_profile_loading():
    cfg = load_profiles(Path("data/voices/mvs_parler_profiles.yaml"))
    q = cfg.speakers["quinn"]
    assert q.engine == "parler"
    assert q.voice == "Will"
    assert q.description and "youthful baritone" in q.description
    assert q.seed == 3471
