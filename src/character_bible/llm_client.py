from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, Optional

import httpx

MOCK_RESPONSE = {
    "name": "unknown",
    "gender": "unknown",
    "approx_age": "unknown",
    "nationality_or_accent_hint": "unknown",
    "role_in_story": "unknown",
    "traits_dialogue": [],
    "pacing": "unknown",
    "energy": "unknown",
    "voice_register": "unknown",
    "notes": {},
}


class LLMClient:
    """Simple HTTP client wrapper for calling an LLM provider."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        seed: Optional[int] = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.seed = seed
        self.timeout = timeout

    async def generate(self, prompt: str) -> str:
        if not self.base_url:
            return self._mock_response()

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
        }
        if self.seed is not None:
            payload["seed"] = self.seed

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
        except Exception:
            return self._mock_response()

        try:
            data = response.json()
        except Exception:
            text = response.text
            return text if text else self._mock_response()

        text = self._extract_text(data)
        if not text:
            return self._mock_response()
        return text

    def generate_sync(self, prompt: str) -> str:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            new_loop = asyncio.new_event_loop()
            policy = asyncio.get_event_loop_policy()
            try:
                policy.set_event_loop(new_loop)
                return new_loop.run_until_complete(self.generate(prompt))
            finally:
                new_loop.close()
                try:
                    policy.set_event_loop(loop)
                except RuntimeError:
                    pass

        return asyncio.run(self.generate(prompt))

    def _extract_text(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            if "output" in data and isinstance(data["output"], str):
                return data["output"]
            if "text" in data and isinstance(data["text"], str):
                return data["text"]
            if "choices" in data and isinstance(data["choices"], list):
                for choice in data["choices"]:
                    if isinstance(choice, dict):
                        message = choice.get("message")
                        if isinstance(message, dict) and isinstance(message.get("content"), str):
                            return message["content"]
                        if isinstance(choice.get("text"), str):
                            return choice["text"]
        if isinstance(data, list) and data and isinstance(data[0], str):
            return data[0]
        return ""

    def _mock_response(self) -> str:
        return json.dumps(MOCK_RESPONSE)


__all__ = ["LLMClient"]
