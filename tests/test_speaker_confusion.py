from abm.audit.speaker_confusion import compute_confusion


def test_compute_confusion():
    base = {
        "chapters": [
            {"title": "c1", "spans": [
                {"type": "Dialogue", "speaker": "A"},
                {"type": "Dialogue", "speaker": "B"},
            ]}
        ]
    }
    refined = {
        "chapters": [
            {"title": "c1", "spans": [
                {"type": "Dialogue", "speaker": "B"},
                {"type": "Dialogue", "speaker": "B"},
            ]}
        ]
    }
    conf = compute_confusion(base, refined)
    assert conf["changes"] == 1
    assert conf["total_compared"] == 2
    assert conf["top_pairs"][0]["from_speaker"] == "A"
