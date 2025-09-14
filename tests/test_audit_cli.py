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
    out_dir = tmp_path / "out"
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
            str(out_dir),
            "--stdout-summary",
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path.cwd() / "src")},
    )
    assert proc.returncode == 0
    assert "Unknown" in proc.stdout
    summary_files = list(out_dir.glob("*.json"))
    assert summary_files, "summary JSON not written"
    summary = json.loads(summary_files[0].read_text())
    assert summary["summary"]["total_spans"] == 1
