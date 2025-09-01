import json
from pathlib import Path

from abm.classifier.classifier_cli import main


def test_classifier_cli_creates_json_outputs(tmp_path: Path) -> None:
    # Create a tiny synthetic input with a TOC and two chapters as JSONL blocks
    blocks = [
        {"text": "Table of Contents"},
        {"text": "Chapter 1: Getting Started .... 2"},
        {"text": "Chapter 2: Next Steps .... 3"},
        {"text": "Some front matter that is not a chapter heading"},
        {"text": "Chapter 1: Getting Started"},
        {"text": "Body paragraph"},
        {"text": "Chapter 2: Next Steps"},
        {"text": "More text"},
    ]
    demo = tmp_path / "demo.jsonl"
    demo.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in blocks) + "\n", encoding="utf-8")

    out_dir = tmp_path / "classified"
    code = main([str(demo), str(out_dir)])
    assert code == 0

    # Check four outputs exist and are non-empty (filenames per classifier_cli)
    for name in (
        "front_matter.json",
        "toc.json",
        "chapters.json",
        "back_matter.json",
    ):
        p = out_dir / name
        assert p.exists(), f"missing {name}"
        assert p.stat().st_size > 0
