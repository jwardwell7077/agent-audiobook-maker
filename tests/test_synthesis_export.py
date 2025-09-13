from __future__ import annotations

import json
from pathlib import Path

from abm.audio.synthesis_export import main as synth_main


def _write_profiles(path: Path) -> None:
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
            }
        ],
        "fallbacks": {"piper": "narrator"},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_tagged(path: Path) -> None:
    data = [
        {
            "index": 1,
            "title": "Ch1",
            "spans": [{"type": "Narration", "speaker": "Narrator", "text": "Hi"}],
        }
    ]
    path.write_text(json.dumps(data), encoding="utf-8")


def test_synthesis_export(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.json"
    tagged_path = tmp_path / "combined.json"
    out_dir = tmp_path / "out"
    _write_profiles(profiles_path)
    _write_tagged(tagged_path)

    synth_main(
        [
            "--tagged",
            str(tagged_path),
            "--profiles",
            str(profiles_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    script_path = out_dir / "scripts" / "ch_001.synth.json"
    manifest_path = out_dir / "synth_manifest.json"
    assert script_path.exists()
    assert manifest_path.exists()
    items = json.loads(script_path.read_text(encoding="utf-8"))
    assert items[0]["text"] == "Hi"
