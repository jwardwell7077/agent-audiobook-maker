from __future__ import annotations

import json
from pathlib import Path

from abm.audio.tts_casting import cast_speaker, spans_to_tasks
from abm.profiles.character_profiles import CharacterProfilesDB


def _make_db(tmp_path: Path) -> CharacterProfilesDB:
    data = {
        "profiles": [
            {
                "id": "narrator",
                "label": "Narrator",
                "engine": "piper",
                "voice": "en_US",
                "refs": [],
                "style": "neutral",
                "tags": ["narrator"],
            },
            {
                "id": "bob",
                "label": "Bob",
                "engine": "piper",
                "voice": "en_US-bob",
                "refs": [],
                "style": "neutral",
                "tags": ["bob"],
            },
        ],
        "map": {"Bob": "bob"},
        "fallbacks": {"piper": "narrator"},
    }
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return CharacterProfilesDB.load(path)


def test_cast_speaker_mapped_unmapped(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    info = cast_speaker("Bob", db)
    assert info["profile_id"] == "bob"
    info2 = cast_speaker("Alice", db, preferred_engine="piper")
    assert info2["profile_id"] == "narrator"


def test_spans_to_tasks(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    spans = [
        {"type": "Narration", "speaker": "Bob", "text": "Hello"},
        {"type": "Dialogue", "speaker": "Alice", "text": "Hi"},
    ]
    tasks = spans_to_tasks(spans, db)
    assert tasks[0]["profile_id"] == "bob"
    assert tasks[1]["profile_id"] == "narrator"
    assert isinstance(tasks[0]["pause_ms"], int)
