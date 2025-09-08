from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model_name: str = "llama3.1:8b-instruct"
    temperature: float = 0.4
    timeout_s: float = 30.0


class OllamaBackend:
    """Tiny adapter to call a local Ollama model.

    This is a placeholder for v1 implementation; wiring and error handling
    will be added per the LLM Attribution spec.
    """

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()

    def generate(self, payload: dict[str, Any]) -> str:
        """Return raw model text for a given payload (placeholder).

        In v1, this will issue an HTTP request to the Ollama API and return
        the model response text. For now, return a minimal JSON string to
        keep integration surfaces stable.
        """
        # Placeholder deterministic output for tests/no-op wiring
        return '{"speaker": "", "confidence": 0.0, "rationale": "noop"}'
