from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from abm.attr.ollama_backend import OllamaBackend, OllamaConfig

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
    base_url: str = "http://localhost:11434"


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
        self._backend = OllamaBackend(
            OllamaConfig(
                base_url=self.config.base_url,
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                timeout_s=self.config.timeout_s,
            )
        )

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
                typ == "dialogue"
                and (not attr.get("speaker") or method == "unknown" or conf < self.config.min_conf_for_skip)
            )

            if not target:
                out.append(rec)
                continue

            # Build compact prompt with context (simple v1 sketch)
            dialogue_text = str(rec.get("text_norm") or rec.get("text_raw") or "")
            # For v1 skeleton, we omit neighbor gathering here; later we will include narration_before/after
            prompt = (
                "You are a careful literary analyst. Given a dialogue line, identify the most likely speaker name.\n"
                "Return JSON only: {\"speaker\": string, \"confidence\": number, \"rationale\": string}.\n"
                "Rules: Do not return Unknown; choose the most plausible proper name.\n\n"
                f"dialogue_text: {json.dumps(dialogue_text)}\n"
            )

            raw = self._backend.generate(prompt)
            parsed: dict[str, Any] | None = None
            for _ in range(max(1, int(self.config.max_json_retries))):
                try:
                    parsed = json.loads(raw)
                    break
                except Exception:
                    # Attempt to extract JSON object if wrapped with commentary
                    start = raw.find("{")
                    end = raw.rfind("}")
                    if 0 <= start < end:
                        try:
                            parsed = json.loads(raw[start : end + 1])
                            break
                        except Exception:
                            pass
                    # As last retry, wrap simple key heuristics
                    raw = '{"speaker": "", "confidence": 0.0, "rationale": "parse_error"}'

            new_attr = dict(attr)
            speaker = ""
            new_conf = conf
            if isinstance(parsed, dict):
                sp = parsed.get("speaker")
                if isinstance(sp, str):
                    speaker = sp.strip()
                c = parsed.get("confidence")
                if isinstance(c, (int, float)):
                    new_conf = max(0.0, min(1.0, float(c)))

            # Simple fallback: if empty speaker, keep previous speaker or leave empty; actual fallback in next iteration
            new_attr["speaker"] = speaker or str(attr.get("speaker") or "")
            new_attr["method"] = "llm"
            new_attr["confidence"] = new_conf
            ev = dict(new_attr.get("evidence") or {})
            ev.update(
                {
                    "prompt_version": self.config.prompt_version,
                    "backend": "ollama",
                    "model": self.config.model_name,
                }
            )
            new_attr["evidence"] = ev

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
