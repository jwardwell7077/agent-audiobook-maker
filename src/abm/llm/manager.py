from __future__ import annotations

"""Utilities to manage a local or remote LLM service.

This module provides a small wrapper around an OpenAI-compatible endpoint
such as `ollama`.  It exposes a dataclass :class:`LLMBackend` describing the
service and :class:`LLMService` helpers for starting, stopping and probing the
server.
"""

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import requests

DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1"


@dataclass
class LLMBackend:
    """Configuration for a local or remote LLM endpoint.

    Attributes:
        kind: Backend type, e.g. ``"ollama"`` or ``"openai_compatible"``.
        endpoint: Base URL of the service.
        model: Default model identifier to pull or query.
        env: Optional environment overrides used when spawning a local service.
    """

    kind: str = "ollama"
    endpoint: str = DEFAULT_ENDPOINT
    model: str = "llama3.1:8b-instruct-q6_K"
    env: dict[str, str] | None = None

    def headers(self) -> dict[str, str]:
        """Build HTTP headers for OpenAI-compatible requests.

        Returns:
            Dict[str, str]: Authorization header carrying an API key.  Ollama
            ignores the value but remote services may require it.
        """

        # OpenAI-compatible header (Ollama ignores the key)
        api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")
        return {"Authorization": f"Bearer {api_key}"}


class LLMService:
    """Manage the lifecycle of a local LLM server.

    Attributes:
        backend: Connection information for the target service.
        _proc: Optional handle to a spawned subprocess running ``ollama``.
    """

    def __init__(self, backend: LLMBackend) -> None:
        """Initialize the service manager.

        Args:
            backend: Configuration describing the target endpoint.
        """

        self.backend = backend
        self._proc: Optional[subprocess.Popen] = None

    def is_alive(self) -> bool:
        """Check whether the LLM endpoint responds to ``/models``.

        Returns:
            bool: ``True`` if a 200 OK response is received, ``False`` otherwise.
        """

        try:
            r = requests.get(f"{self.backend.endpoint}/models", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def ensure_up(self, timeout_s: float = 30.0) -> None:
        """Start the service if necessary and wait for readiness.

        Args:
            timeout_s: Maximum time in seconds to wait for the endpoint.

        Raises:
            TimeoutError: If the endpoint does not respond before ``timeout_s``.
        """

        if self.is_alive():
            return
        if self.backend.kind == "ollama":
            env = os.environ.copy()
            if self.backend.env:
                env.update(self.backend.env)
            # Spawn the Ollama server in a detached session.
            self._proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
        self._wait_ready(timeout_s)

    def _wait_ready(self, timeout_s: float) -> None:
        """Poll the endpoint until it responds or ``timeout_s`` elapses."""

        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self.is_alive():
                return
            time.sleep(0.3)
        raise TimeoutError(f"LLM endpoint not ready at {self.backend.endpoint}")

    def stop(self, timeout_s: float = 8.0) -> None:
        """Terminate a spawned Ollama server if running.

        Args:
            timeout_s: Seconds to wait for graceful shutdown.
        """

        if not self._proc:
            return
        try:
            os.killpg(os.getpgid(self._proc.pid), signal.SIGINT)
        except Exception:
            pass
        try:
            self._proc.wait(timeout=timeout_s)
        except Exception:
            pass
        self._proc = None

    def pull_model(self, model: str | None = None) -> None:
        """Ensure the requested model is available locally.

        Args:
            model: Optional model name; defaults to :attr:`LLMBackend.model`.
        """

        if self.backend.kind != "ollama":
            return
        name = model or self.backend.model
        subprocess.run(["ollama", "pull", name], check=True)

