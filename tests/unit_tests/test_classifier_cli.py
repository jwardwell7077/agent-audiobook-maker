from pathlib import Path
from abm.classifier.classifier_cli import main


def test_classifier_cli_creates_json_outputs(tmp_path: Path) -> None:
    # Use bundled demo text that mimics a public domain sample with TOC.
    demo = Path(
        "tests/data/books/public_domain_demo/public_domain_demo.txt"
    )
    assert demo.exists(), "demo input missing"

    out_dir = tmp_path / "classified"
    code = main([str(demo), str(out_dir)])  # type: ignore[arg-type]
    assert code == 0

    # Check four outputs exist and are non-empty
    for name in (
        "front_matter.json",
        "toc.json",
        "chapters_section.json",
        "back_matter.json",
    ):
        p = out_dir / name
        assert p.exists(), f"missing {name}"
        assert p.stat().st_size > 0
