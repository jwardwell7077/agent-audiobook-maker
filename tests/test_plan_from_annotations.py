import json
from pathlib import Path

import pytest

from abm.voice.plan_from_annotations import build_plans


def _make_profiles(tmp_path: Path) -> Path:
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
        "map": {"Narrator": "narrator", "Bob": "bob"},
        "fallbacks": {"piper": "narrator"},
    }
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_plan_builder(tmp_path: Path) -> None:
    combined = {
        "chapters": [
            {
                "chapter_index": 1,
                "title": "Test",
                "spans": [
                    {
                        "id": "s1",
                        "type": "Narration",
                        "speaker": "Narrator",
                        "text": (
                            "This is a long narration, which should be split into pieces. "
                            "Another sentence follows."
                        ),
                    },
                    {
                        "id": "s2",
                        "type": "Dialogue",
                        "speaker": "Bob",
                        "text": "Hello there,",
                    },
                ],
            }
        ]
    }
    combined_path = tmp_path / "combined.json"
    combined_path.write_text(json.dumps(combined), encoding="utf-8")
    profiles_path = _make_profiles(tmp_path)
    out_dir = tmp_path / "plans"
    build_plans(
        combined_path,
        profiles_path,
        out_dir,
        sample_rate=48000,
        crossfade_ms=120,
        max_chars=40,
        pause_narr=120,
        pause_dialog=80,
        pause_thought=140,
        prefer_engine="piper",
    )
    plan_path = out_dir / "ch_0001.json"
    plan = json.loads(plan_path.read_text())
    assert plan["sample_rate"] == 48000
    assert plan["crossfade_ms"] == 120
    assert len(plan["segments"]) == 4
    assert plan["segments"][0]["kind"] == "Narration"
    assert plan["segments"][0]["style"]["pace"] == pytest.approx(0.98)
    assert plan["segments"][3]["pause_ms"] == 160
