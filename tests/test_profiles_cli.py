from __future__ import annotations

import json
import textwrap
from pathlib import Path

from abm.profiles import load_profiles, resolve_speaker
from abm.profiles.profiles_cli import main


def _write_profiles(tmp_path: Path) -> Path:
    text = """
    version: 1
    defaults:
      engine: piper
      narrator_voice: base
    speakers:
      Narrator:
        engine: piper
        voice: base
      Alice:
        engine: piper
        voice: alice
    """
    p = tmp_path / "profiles.yaml"
    p.write_text(textwrap.dedent(text))
    return p


def _write_annotations(tmp_path: Path, include_unknown: bool) -> Path:
    spans = [
        {"type": "Dialogue", "speaker": "Alice", "text": "hi"},
        {"type": "Narration", "speaker": "Narrator", "text": "story"},
    ]
    if include_unknown:
        spans.append({"type": "Dialogue", "speaker": "Ghost", "text": "boo"})
    ann = {"chapters": [{"spans": spans}]}
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(ann))
    return p


def test_audit_cli(tmp_path: Path) -> None:
    profiles = _write_profiles(tmp_path)
    ann_bad = _write_annotations(tmp_path, True)
    out = tmp_path / "report.json"
    rc = main(
        [
            "audit",
            "--profiles",
            str(profiles),
            "--annotations",
            str(ann_bad),
            "--out",
            str(out),
        ]
    )
    assert rc == 2

    ann_good = _write_annotations(tmp_path, False)
    out2 = tmp_path / "report.md"
    rc = main(
        [
            "audit",
            "--profiles",
            str(profiles),
            "--annotations",
            str(ann_good),
            "--out",
            str(out2),
        ]
    )
    assert rc == 0 and out2.exists()


def test_generate_cli(tmp_path: Path) -> None:
    ann = {
        "chapters": [
            {
                "spans": [
                    {"type": "Dialogue", "speaker": "Alice", "text": "hi"},
                    {"type": "Dialogue", "speaker": "Bob", "text": "hello"},
                    {"type": "Dialogue", "speaker": "Alice", "text": "again"},
                ]
            }
        ]
    }
    ann_path = tmp_path / "ann.json"
    ann_path.write_text(json.dumps(ann))
    out_path = tmp_path / "out.yaml"
    rc = main(
        [
            "generate",
            "--annotations",
            str(ann_path),
            "--out",
            str(out_path),
            "--n-top",
            "2",
        ]
    )
    assert rc == 0
    cfg = load_profiles(out_path)
    assert cfg.version == 1
    assert resolve_speaker(cfg, "Alice") is not None
