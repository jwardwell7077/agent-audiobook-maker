import json
import subprocess
import sys
from pathlib import Path


def _write_doc(path: Path, speaker="A"):
    doc = {"chapters": [{"title": "c1", "spans": [{"type": "Dialogue", "speaker": speaker}]}]}
    path.write_text(json.dumps(doc))


def test_cli_smoke(tmp_path):
    refined = tmp_path / "refined.json"
    base = tmp_path / "base.json"
    metrics = tmp_path / "m.jsonl"
    _write_doc(refined)
    _write_doc(base)
    metrics.write_text("{}\n")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "abm.audit",
            "--refined",
            str(refined),
            "--base",
            str(base),
            "--metrics-jsonl",
            str(metrics),
            "--out-dir",
            str(tmp_path / "out"),
            "--stdout-summary",
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path.cwd()/"src")},
    )
    assert proc.returncode == 0
    assert "Unknown" in proc.stdout
