import json
from pathlib import Path

from abm.profiles.alias_resolver import (
    ResolverConfig,
    Proposal,
    apply_proposals,
    normalize_name,
    propose_aliases,
    save_artifacts,
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
    proposals = propose_aliases(refined, db, ResolverConfig(tau_auto=0.0, tau_review=0.0))
    assert proposals[0].candidate == "Alice"


def test_apply_proposals_dedup(tmp_path):
    refined = {"items": [{"speaker": "Alyce"}]}
    db = _make_db(tmp_path)
    proposals = propose_aliases(refined, db, ResolverConfig(tau_auto=0.0, tau_review=0.0))
    apply_proposals(proposals, db)
    apply_proposals(proposals, db)
    assert list(db.speaker_map.keys()).count("Alyce") == 1


def test_save_artifacts(tmp_path):
    proposals = [
        Proposal(
            mention="Alyce",
            normalized="alyce",
            cluster_id="alyce",
            candidate="Alice",
            score=0.9,
            evidence={},
            decision="auto",
        ),
        Proposal(
            mention="Ally",
            normalized="ally",
            cluster_id="ally",
            candidate="Alice",
            score=0.7,
            evidence={},
            decision="review",
        ),
    ]
    save_artifacts(proposals, tmp_path)
    assert (tmp_path / "proposals.jsonl").exists()
    assert (tmp_path / "alias_patch.yaml").exists()
    assert (tmp_path / "review_queue.md").exists()
