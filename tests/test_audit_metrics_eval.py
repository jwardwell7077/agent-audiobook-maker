from pathlib import Path

from abm.audit.metrics_eval import compute_basic_metrics


def test_compute_basic_metrics():
    refined = {
        "chapters": [
            {"title": "c1", "spans": [
                {"type": "Dialogue", "speaker": "A", "text": "hi"},
                {"type": "Thought", "speaker": "Unknown", "text": "hmm"},
            ]},
            {"title": "c2", "spans": [
                {"type": "Dialogue", "speaker": "B", "text": "yo"}
            ]},
        ]
    }
    base = {
        "chapters": [
            {"title": "c1", "spans": [
                {"type": "Dialogue", "speaker": "A", "text": "hi"},
                {"type": "Thought", "speaker": "B", "text": "hmm"},
            ]},
            {"title": "c2", "spans": [
                {"type": "Dialogue", "speaker": "C", "text": "yo"}
            ]},
        ]
    }
    summary = compute_basic_metrics(refined, base, worst_n=5)
    assert summary["total_spans"] == 3
    assert summary["unknown_count"] == 1
    assert summary["speaker_changes"] == 2
    assert summary["worst_chapters"][0]["title"] == "c1"
