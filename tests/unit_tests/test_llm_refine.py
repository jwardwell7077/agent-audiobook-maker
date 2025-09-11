"""Tests for merging LLM refinement results."""

import json

from abm.annotate.llm_refine import LLMRefineConfig, LLMRefiner


def test_refine_updates_span(tmp_path, monkeypatch) -> None:
    chapters = {
        "chapters": [
            {
                "chapter_index": 0,
                "title": "Ch1",
                "text": "Hi",
                "roster": {"Alice": ["Alice"]},
                "spans": [
                    {
                        "id": 1,
                        "type": "Dialogue",
                        "speaker": "Unknown",
                        "start": 0,
                        "end": 2,
                        "text": "Hi",
                        "method": "rule:unknown",
                        "confidence": 0.3,
                    }
                ],
            }
        ]
    }
    chapters_path = tmp_path / "chapters_tagged.json"
    chapters_path.write_text(json.dumps(chapters), encoding="utf-8")

    cand = {
        "chapter_index": 0,
        "chapter_title": "Ch1",
        "span_id": 1,
        "span_type": "Dialogue",
        "baseline_speaker": "Unknown",
        "baseline_method": "rule:unknown",
        "baseline_confidence": 0.3,
        "text": "Hi",
        "context_before": "",
        "context_after": "",
        "roster": ["Alice"],
        "notes": None,
        "fingerprint": "fp",
    }
    cand_path = tmp_path / "cands.jsonl"
    cand_path.write_text(json.dumps(cand), encoding="utf-8")

    out_json = tmp_path / "out.json"
    cfg = LLMRefineConfig(cache_path=tmp_path / "cache.json")
    refiner = LLMRefiner(cfg)

    def fake_consensus(self, cand):
        return "Alice", 0.95

    monkeypatch.setattr(LLMRefiner, "_consensus", fake_consensus)

    refiner.refine(chapters_path, cand_path, out_json)
    result = json.loads(out_json.read_text(encoding="utf-8"))
    span = result["chapters"][0]["spans"][0]
    assert span["speaker"] == "Alice"
    assert span["confidence"] == 0.95
    assert span["method"] == "llm:consensus"


def test_accept_and_consensus(monkeypatch) -> None:
    cfg = LLMRefineConfig(votes=3)
    ref = LLMRefiner(cfg)

    # _accept logic
    assert ref._accept("Unknown", 0.1, "Alice", 0.2)
    assert not ref._accept("Bob", 0.5, "Bob", 0.8)
    assert not ref._accept("Bob", 0.5, "Alice", 0.53)
    assert ref._accept("Bob", 0.5, "Alice", 0.56)

    # _consensus voting: majority label wins with highest confidence among winners
    responses = [("A", 0.8), ("B", 0.9), ("A", 0.7)]

    def fake_ask(self, cand, variant):
        return responses[variant]

    monkeypatch.setattr(LLMRefiner, "_ask_llm", fake_ask)
    speaker, conf = ref._consensus({})
    assert speaker == "A"
    assert conf == 0.8


def test_ask_llm_cache(monkeypatch) -> None:
    cfg = LLMRefineConfig(cache_path=None)
    ref = LLMRefiner(cfg)

    cand = {
        "span_id": 1,
        "text": "Hi",
        "context_before": "a" * 400,
        "context_after": "b" * 400,
        "roster": [],
        "baseline_speaker": "Unknown",
        "baseline_method": "rule:unknown",
        "baseline_confidence": 0.0,
        "span_type": "Dialogue",
        "notes": None,
    }

    calls = {"count": 0}

    def fake_post(url, headers, json, timeout):
        calls["count"] += 1

        class Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {
                    "choices": [{"message": {"content": '{"speaker": "Bob", "confidence": 0.9}'}}]
                }

        return Resp()

    monkeypatch.setattr(ref._session, "post", fake_post)
    spk1, _ = ref._ask_llm(cand, variant=0)
    spk2, _ = ref._ask_llm(cand, variant=0)
    assert spk1 == spk2 == "Bob"
    assert calls["count"] == 1

    # prompt variants produce different content
    p0 = ref._build_prompt(cand, 0)
    p1 = ref._build_prompt(cand, 1)
    p2 = ref._build_prompt(cand, 2)
    assert p0 != p1 and p1 != p2 and p0 != p2

