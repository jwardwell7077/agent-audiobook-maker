from __future__ import annotations

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, FloatInput, Output, StrInput
from langflow.schema import Data

from abm.attr.llm_attribution import LLMAttrConfig, LLMAttributor


class ABMLLMAttribution(Component):
    display_name = "ABM LLM Attribution"
    description = "Resolve dialogue speakers using a local LLM with caching and fallbacks"
    icon = "user"
    name = "ABMLLMAttribution"

    inputs = [
        DataInput(name="spans_attr", display_name="Attributed Spans (heuristic)", required=True),
        StrInput(name="model_name", display_name="Model", value="llama3.1:8b-instruct", required=False),
        StrInput(name="base_url", display_name="Ollama URL", value="http://localhost:11434", required=False),
        FloatInput(name="temperature", display_name="Temperature", value=0.4, required=False),
        FloatInput(name="min_conf_for_skip", display_name="Min conf for skip", value=0.85, required=False),
        FloatInput(name="context_radius", display_name="Context radius (spans)", value=4.0, required=False),
        StrInput(name="prompt_version", display_name="Prompt version", value="v1", required=False),
        FloatInput(name="timeout_s", display_name="Timeout (s)", value=30.0, required=False),
        StrInput(name="cache_dir", display_name="Cache dir", value=".cache/abm", required=False),
        BoolInput(name="write_to_disk", display_name="Write artifacts", value=False, required=False),
        BoolInput(name="re_attribute_all", display_name="Re-attribute all (exp)", value=False, required=False),
    ]

    outputs = [
        Output(display_name="LLM Attributed Spans", name="spans_attr_llm", method="attribute"),
        Output(display_name="LLM Attribution Meta", name="meta", method="get_meta"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last: tuple[list[dict], dict] | None = None

    def _ensure(self) -> tuple[list[dict], dict]:
        if self._last is not None:
            return self._last
        src = getattr(self, "spans_attr", None)
        if src is None:
            raise TypeError("spans_attr is required")
        payload = src.data if hasattr(src, "data") else src
        spans_attr = payload.get("spans_attr") or payload.get("spans") or []
        if not isinstance(spans_attr, list):
            raise TypeError("spans_attr must be a list payload")
        cfg = LLMAttrConfig(
            context_radius=int(float(getattr(self, "context_radius", 4.0) or 4.0)),
            max_json_retries=2,
            temperature=float(getattr(self, "temperature", 0.4) or 0.4),
            min_conf_for_skip=float(getattr(self, "min_conf_for_skip", 0.85) or 0.85),
            cache_dir=str(getattr(self, "cache_dir", ".cache/abm") or ".cache/abm"),
            model_name=str(getattr(self, "model_name", "llama3.1:8b-instruct") or "llama3.1:8b-instruct"),
            prompt_version=str(getattr(self, "prompt_version", "v1") or "v1"),
            timeout_s=float(getattr(self, "timeout_s", 30.0) or 30.0),
            re_attribute_all=bool(getattr(self, "re_attribute_all", False)),
        )
        attributor = LLMAttributor(cfg)
        res, meta = attributor.run(spans_attr)
        self._last = (res, meta)
        return self._last

    def attribute(self) -> Data:
        spans, _ = self._ensure()
        return Data(data={"spans_attr": spans})

    def get_meta(self) -> Data:
        _, meta = self._ensure()
        return Data(data=meta)
