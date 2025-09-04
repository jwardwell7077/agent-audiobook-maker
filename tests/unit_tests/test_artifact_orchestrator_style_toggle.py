from abm.lf_components.audiobook.abm_artifact_orchestrator import ABMArtifactOrchestrator


def test_orchestrator_emits_spans_style_when_enabled():
    # Minimal blocks_data payload for validator to work
    blocks_data = {
        "blocks_data": {
            "book_name": "test_book",
            "chapter_index": 0,
            "blocks": [
                {"text": 'He said, "Hello."'},
                {"text": "Then he walked away."},
            ],
        }
    }

    orch = ABMArtifactOrchestrator(
        blocks_data=blocks_data["blocks_data"],
        write_to_disk=False,
        enable_style_planner=True,
    )
    out = orch.generate_artifacts().data
    assert out.get("spans_style") is not None, "Style planner output missing"
    assert isinstance(out["spans_style"], list) and len(out["spans_style"]) >= 1
