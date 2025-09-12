"""Tests for Stage B LLM refinement utilities."""

import json

from abm.annotate.llm_refine import LLMRefineConfig, refine_document
from abm.llm.manager import LLMBackend
from abm.llm.client import OpenAICompatClient
from abm.annotate.llm_cache import LLMCache


def test_refine_document_updates_span(tmp_path, monkeypatch) -> None:
    """LLM refinement should modify spans and write summary."""
    doc = {
        "chapters": [
            {
                "chapter_index": 0,
                "title": "Ch1",
                "text": "Hi",
                "roster": {"Alice": ["Alice"]},
                "spans": [
                    {
                        "start": 0,
                        "end": 2,
                        "type": "Dialogue",
                        "speaker": "Unknown",
                        "confidence": 0.3,
                    }
                ],
            }
        ]
    }
    tagged_path = tmp_path / "combined.json"
    tagged_path.write_text(json.dumps(doc), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "review.md"
    cache_path = tmp_path / "cache.sqlite"

    backend = LLMBackend(endpoint="http://dummy")
    cfg = LLMRefineConfig(votes=2)

    calls = {"n": 0}

    def fake_chat_json(self, system_prompt, user_prompt, temperature, top_p, max_tokens):
        calls["n"] += 1
        return {"speaker": "Alice", "confidence": 0.95}

    monkeypatch.setattr(OpenAICompatClient, "chat_json", fake_chat_json)

    refine_document(tagged_path, out_json, out_md, backend, cfg, manage_service=False, cache_path=cache_path)

    result = json.loads(out_json.read_text(encoding="utf-8"))
    span = result["chapters"][0]["spans"][0]
    assert span["speaker"] == "Alice"
    assert span["method"] == "llm"
    assert span["confidence"] >= 0.95
    assert calls["n"] == 2  # votes

    md = out_md.read_text(encoding="utf-8")
    assert "candidates processed" in md


def test_llm_cache_roundtrip(tmp_path) -> None:
    """Cache should store and retrieve LLM decisions."""

    cache = LLMCache(tmp_path / "c.sqlite")
    key_args = {
        "roster": {"A": []},
        "left": "a",
        "mid": "b",
        "right": "c",
        "span_type": "Dialogue",
        "model": "m",
    }
    assert cache.get(**key_args) is None
    cache.set({"speaker": "A", "confidence": 0.9}, **key_args)
    assert cache.get(**key_args) == {"speaker": "A", "confidence": 0.9}
    cache.close()

