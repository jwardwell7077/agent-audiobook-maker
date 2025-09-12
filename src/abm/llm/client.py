from __future__ import annotations

"""Thin OpenAI-compatible JSON chat client.

This module intentionally implements only the minimal pieces required for the
refinement pipeline.  It sends a chat completion request and expects the model
to return JSON content.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict

import requests


@dataclass
class OpenAICompatClient:
    """Minimal OpenAI-compatible chat client returning JSON content.

    Attributes:
        base_url: Endpoint to send requests to.
        api_key: API key for remote services.  Ignored by ``ollama``.
        model: Model identifier to query.
        timeout_s: Request timeout in seconds.
    """

    base_url: str
    api_key: str = "EMPTY"  # ignored by Ollama
    model: str = "llama3.1:8b-instruct-q6_K"
    timeout_s: int = 120

    def _headers(self) -> Dict[str, str]:
        """Return authorization headers for a request.

        Returns:
            Dict[str, str]: Mapping with the ``Authorization`` header.

        Raises:
            None: This helper does not raise exceptions.
        """

        return {"Authorization": f"Bearer {self.api_key}"}

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = 128,
    ) -> Dict[str, Any]:
        """Send prompts and parse JSON reply from the model.

        Args:
            system_prompt: Instructional system message.
            user_prompt: User message containing the task.
            temperature: Sampling temperature for the model.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens in the response.

        Returns:
            Dict[str, Any]: Parsed JSON response.  If parsing fails, a fallback
            object with ``speaker``, ``confidence`` and raw content is returned.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except Exception:
            # Return a best-effort structure to avoid crashing callers.
            return {"speaker": "Unknown", "confidence": 0.0, "raw": content}

