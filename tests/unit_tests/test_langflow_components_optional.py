from __future__ import annotations

from pathlib import Path

import json

import pytest

from abm.langflow_runner import run as run_flow


def test_langflow_runner_mvs_optional(tmp_path: Path) -> None:
    """Optional smoke test for component chain using local mvs chapters.

    Skips if data/clean/mvs/chapters.json is not present locally.
    """
    chapters = Path("data/clean/mvs/chapters.json")
    if not chapters.exists():
        pytest.skip("mvs chapters.json not present; skipping")

    out = run_flow("mvs", out_stem="segments_test", base_dir=str(Path.cwd()))
    p = Path(out)
    assert p.exists(), "output JSONL not created"
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 1, "should have header + at least one utterance"
    header = json.loads(lines[0])
    assert "header" in header and header["header"]["book"] == "mvs"
