from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMAttrConfig:
    context_radius: int = 4
    max_json_retries: int = 2
    temperature: float = 0.4
    min_conf_for_skip: float = 0.85
    cache_dir: str = ".cache/abm"
    model_name: str = "llama3.1:8b-instruct"
    prompt_version: str = "v1"
    timeout_s: float = 30.0
    re_attribute_all: bool = False


def _cache_key(payload: dict[str, Any]) -> str:
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class LLMAttributor:
    """LLM Attribution orchestrator (skeleton).

    Implements selection of target spans and prepares prompts/contexts.
    JSON parsing, retries, and fallbacks to be implemented per spec.
    """

    def __init__(self, config: LLMAttrConfig | None = None) -> None:
        self.config = config or LLMAttrConfig()

    def run(self, spans_attr: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        out: list[dict[str, Any]] = []
        cache_hits = 0
        cache_misses = 0

        for rec in spans_attr:
            typ = (rec.get("type") or rec.get("role") or "").lower()
            attr = rec.get("attribution") or {}
            conf = float(attr.get("confidence") or 0.0)
            method = str(attr.get("method") or "")

            target = self.config.re_attribute_all or (
                typ == "dialogue" and (
                    not attr.get("speaker") or method == "unknown" or conf < self.config.min_conf_for_skip
                )
            )

            if not target:
                out.append(rec)
                continue

            # Placeholder: pass-through with marker, to be replaced by real LLM logic
            new_attr = dict(attr)
            new_attr.setdefault("speaker", attr.get("speaker") or "")
            new_attr["method"] = "llm_fallback_placeholder"
            new_attr.setdefault("confidence", conf)
            new_attr.setdefault("evidence", {})
            new_attr["evidence"]["qa_flags"] = ["placeholder"]

            new_rec = dict(rec)
            new_rec["attribution"] = new_attr
            out.append(new_rec)
            cache_misses += 1

        meta = {
            "component": "LLMAttributor",
            "prompt_version": self.config.prompt_version,
            "model_name": self.config.model_name,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
        }
        return out, meta
