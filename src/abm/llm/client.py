"""Thin OpenAI-compatible JSON chat client.

This module intentionally implements only the minimal pieces required for the
refinement pipeline.  It sends a chat completion request and expects the model
to return JSON content.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


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

    def _headers(self) -> dict[str, str]:
        """Return authorization headers for a request.

        Returns:
            Dict[str, str]: Mapping with the ``Authorization`` header.

        Raises:
            None: This helper does not raise exceptions.
        """

        return {"Authorization": f"Bearer {self.api_key}"}

    def _post_openai_v1(self, payload: dict[str, Any]) -> requests.Response:
        """POST to an OpenAI v1-compatible endpoint.

        Tries ``{base_url}/chat/completions``.

        Args:
            payload: Request body.

        Returns:
            requests.Response: The HTTP response.

        Raises:
            requests.HTTPError: If the HTTP request fails (non-2xx).
        """

        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        return r

    def _post_ollama_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> requests.Response:
        """POST to Ollama's native chat endpoint ``/api/chat``.

        This is used as a fallback when an OpenAI v1 route is not available.

        Returns a Response object whose JSON includes ``message.content``.
        """

        # If base_url ends with "/v1", strip it for Ollama native API.
        base = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        base = base.rstrip("/")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # Encourage JSON outputs and disable streaming for simpler parsing.
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                # num_predict controls max new tokens in Ollama
                "num_predict": max_tokens,
            },
        }
        r = requests.post(
            f"{base}/api/chat",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        return r

    def _post_ollama_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> requests.Response:
        """POST to Ollama's legacy generate endpoint ``/api/generate``.

        Some Ollama versions do not provide ``/api/chat``. This endpoint returns
        a JSON object containing a ``response`` field when ``stream=False``.
        """

        base = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        base = base.rstrip("/")
        payload = {
            "model": self.model,
            # Modern Ollama supports a separate system field; keep prompt minimal.
            "system": system_prompt,
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        r = requests.post(
            f"{base}/api/generate",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        return r

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = 128,
    ) -> dict[str, Any]:
        """Send prompts and parse JSON reply from the model.

        Args:
            system_prompt: Instructional system message.
            user_prompt: User message containing the task.
            temperature: Sampling temperature for the model.
            top_p: Nucleus sampling parameter.
            max_tokens: Maximum tokens in the response.

        Returns:
            Dict[str, Any]: Parsed JSON response.  If parsing fails, a fallback
            object with ``speaker``, ``confidence`` and ``raw`` fields is
            returned.

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
        # First, try OpenAI v1-compatible route.
        try:
            r = self._post_openai_v1(payload)
            content = r.json()["choices"][0]["message"]["content"]
        except requests.HTTPError as http_err:
            # If the route isn't available (404) or method not allowed, try Ollama native.
            status = getattr(http_err.response, "status_code", None)
            if status in (404, 405):
                # Some installations provide /api/chat, others only /api/generate.
                try:
                    r = self._post_ollama_chat(
                        system_prompt,
                        user_prompt,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                    )
                    content = r.json().get("message", {}).get("content", "")
                except requests.HTTPError as http_err2:
                    status2 = getattr(http_err2.response, "status_code", None)
                    if status2 in (404, 405):
                        r = self._post_ollama_generate(
                            system_prompt,
                            user_prompt,
                            temperature=temperature,
                            top_p=top_p,
                            max_tokens=max_tokens,
                        )
                        content = r.json().get("response", "")
                    else:
                        raise
            else:
                raise
        except requests.RequestException:
            # Network error; attempt Ollama native as a fallback once.
            try:
                r = self._post_ollama_chat(
                    system_prompt,
                    user_prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                content = r.json().get("message", {}).get("content", "")
            except requests.RequestException:
                r = self._post_ollama_generate(
                    system_prompt,
                    user_prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )
                content = r.json().get("response", "")
        try:
            obj = json.loads(content)
            # Be tolerant: ensure we return a dict[str, Any].
            if isinstance(obj, dict):
                return obj
            # Wrap non-dict JSON into a standard structure.
            return {"value": obj}
        except Exception as exc:
            logger.debug("Failed to parse JSON content: %s", exc)
            # Return a best-effort structure to avoid crashing callers.
            return {"speaker": "Unknown", "confidence": 0.0, "raw": content}
