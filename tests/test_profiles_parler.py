from pathlib import Path

import pytest

from abm.profiles import load_profiles
from abm.profiles.character_profiles import HAVE_YAML


pytestmark = pytest.mark.skipif(not HAVE_YAML, reason="PyYAML not installed")


def test_parler_profile_loading():
    cfg = load_profiles(Path("data/voices/mvs_parler_profiles.yaml"))
    q = cfg.speakers["quinn"]
    assert q.engine == "parler"
    assert q.voice == "Will"
    assert q.description and "youthful baritone" in q.description
    assert q.seed == 3471
