from pathlib import Path


def test_examples_spans_first_flow_exists() -> None:
    p = Path("examples/langflow/abm_spans_first_pipeline.v15.json")
    assert p.exists(), "Expected example flow JSON to exist"
    assert p.stat().st_size > 0
