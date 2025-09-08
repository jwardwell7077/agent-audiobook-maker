from __future__ import annotations

import json
import urllib.error
import urllib.request
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

    def generate(self, prompt: str) -> str:
        """Call Ollama /api/generate and return the response text.

        Sends a non-streaming request with temperature and timeout.
        Raises URLError/HTTPError on transport issues.
        """
        url = f"{self.config.base_url.rstrip('/')}/api/generate"
        body = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.config.temperature},
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:  # nosec B310
            raw = resp.read().decode("utf-8", errors="replace")
        # Ollama returns a JSON object with a 'response' field
        try:
            parsed: dict[str, Any] = json.loads(raw)
            return str(parsed.get("response") or "")
        except Exception:
            # If the API returns plain text (unlikely), pass it through as string
            return str(raw)
