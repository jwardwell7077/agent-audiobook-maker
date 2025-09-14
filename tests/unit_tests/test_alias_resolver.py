import json
from pathlib import Path

from abm.profiles.alias_resolver import (
    ResolverConfig,
    normalize_name,
    propose_aliases,
)
from abm.profiles.character_profiles import CharacterProfilesDB, Profile


def _make_db(tmp_path: Path) -> CharacterProfilesDB:
    db = CharacterProfilesDB(
        profiles={"p1": Profile(id="p1", label="Alice", engine="e", voice="v", refs=[], style="")},
        speaker_map={"Alice": "p1"},
    )
    db_path = tmp_path / "profiles.json"
    db.save(db_path)
    return CharacterProfilesDB.load(db_path)


def test_normalize_name_basic():
    assert normalize_name(" I Alice! ") == "alice"


def test_propose_aliases_basic(tmp_path):
    refined = {"items": [{"speaker": "Alyce"}]}
    db = _make_db(tmp_path)
    proposals = propose_aliases(refined, db, ResolverConfig())
    assert proposals[0].candidate == "Alice"
