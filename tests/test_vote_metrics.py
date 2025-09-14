from pathlib import Path
import json

from abm.audit.vote_metrics import parse_metrics_jsonl


def test_parse_metrics_jsonl(tmp_path):
    path = tmp_path / "m.jsonl"
    events = [
        {"cache_hit": True, "votes": {"A": 3}, "chapter": 1, "span_index": 0, "title": "c1"},
        {"cache_hit": False, "votes": {"A": 2, "B": 1}, "chapter": 1, "span_index": 1, "title": "c1"},
        {"cache_hit": False, "votes": {"A": 1, "B": 1}, "chapter": 2, "span_index": 0, "title": "c2"},
    ]
    with path.open("w", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    stats = parse_metrics_jsonl(path)
    assert stats["cache_hits"] == 1
    assert stats["cache_misses"] == 2
    assert len(stats["vote_margins"]) == 3
    assert len(stats["weak_cases"]) == 2
