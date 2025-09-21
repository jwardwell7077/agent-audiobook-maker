# isort: skip_file
"""Kokoro TTS adapter (HTTP, OpenAI-compatible endpoint).

This adapter talks to a Kokoro-FastAPI compatible server exposing
POST /v1/audio/speech and returns WAV bytes. It integrates with the
generic :class:`TTSAdapter` interface used by the audiobook MVS.

Environment variables:
    KOKORO_URL     Default http://127.0.0.1:8880
    KOKORO_TIMEOUT Request timeout in seconds (default 120)

Style handling:
    If ``task.style`` contains a token like "speed=1.02" (or "pace=1.02"),
    it will be parsed and forwarded to the engine. The adapter is otherwise
    agnostic to style strings.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import requests  # type: ignore[import-untyped]
import soundfile as sf  # type: ignore[import-untyped]

from abm.audio.tts_base import SynthesisError, TTSAdapter, TTSTask


_RE_NUM = r"[0-9]+(?:\.[0-9]+)?"


def _parse_speed(style: Any) -> float | None:
    if style is None:
        return None
    # Style as dict: honor 'pace' or 'speed'
    if isinstance(style, dict):
        for k in ("speed", "pace"):
            if k in style and isinstance(style[k], int | float):
                try:
                    return float(style[k])
                except Exception:
                    pass
        return None
    # Style as string: parse tokens like "speed=1.02"
    s = str(style)
    m = re.search(rf"\b(?:speed|pace)=({_RE_NUM})\b", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None


def _parse_seed(style: Any) -> int | None:
    if style is None:
        return None
    if isinstance(style, dict):
        v = style.get("seed")
        if isinstance(v, int | str) and str(v).isdigit():
            try:
                return int(v)
            except Exception:
                return None
        return None
    s = str(style)
    m = re.search(r"\bseed=([0-9]+)\b", s, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


class KokoroSynthesisError(SynthesisError):
    pass


@dataclass(frozen=True)
class _AdapterConfig:
    url: str
    timeout_s: int


class KokoroAdapter(TTSAdapter):
    """HTTP client adapter for Kokoro-FastAPI.

    Args:
        url: Base URL (default from KOKORO_URL or http://127.0.0.1:8880).
        timeout_s: Request timeout seconds (default from env or 120).
        default_voice: Optional voice used when ``task.voice`` is missing.
    """

    def __init__(self, url: str | None = None, timeout_s: int | None = None, default_voice: str | None = None) -> None:
        base_url = str(url or os.getenv("KOKORO_URL", "http://127.0.0.1:8880"))
        timeout = int(timeout_s or int(os.getenv("KOKORO_TIMEOUT", "90")))
        self._cfg = _AdapterConfig(url=base_url.rstrip("/"), timeout_s=timeout)
        self._default_voice = default_voice

    # Adapter version contributes to cache keys via TTSManager
    @staticmethod
    def version() -> str:  # pragma: no cover - trivial
        return "kokoro-http-v1"

    def preload(self) -> None:  # pragma: no cover - no warmup required
        return None

    def _post_tts(self, payload: dict[str, Any]) -> bytes:
        url = f"{self._cfg.url}/v1/audio/speech"
        # Basic retry on 429/5xx
        backoffs = [0.5, 1.0]
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = requests.post(url, json=payload, timeout=self._cfg.timeout_s)
            except requests.RequestException as e:  # pragma: no cover - network error
                raise KokoroSynthesisError(f"Kokoro request failed: {e}") from e
            if resp.status_code == 200:
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if "audio" in ctype or "octet-stream" in ctype:
                    return bytes(resp.content)
                # Try JSON envelope with base64
                try:
                    data = resp.json()
                except Exception as exc:
                    body = resp.text[:200]
                    raise KokoroSynthesisError(
                        f"Kokoro returned 200 but not audio/JSON (body starts: {body!r})"
                    ) from exc
                b64 = (
                    data.get("audio")
                    or data.get("wav_base64")
                    or data.get("data")
                    or (data.get("choices", [{}])[0] or {}).get("audio")
                )
                if not b64:
                    body = json.dumps(data)[:200]
                    raise KokoroSynthesisError(f"Kokoro JSON response missing audio field (got: {body})")
                try:
                    b64s = str(b64)
                    if b64s.startswith("data:"):
                        b64s = b64s.split(",", 1)[-1]
                    return base64.b64decode(b64s)
                except Exception as e:  # pragma: no cover
                    raise KokoroSynthesisError(f"Invalid base64 audio from Kokoro: {e}") from e
            if resp.status_code in {429, 500, 502, 503, 504} and backoffs:
                time.sleep(backoffs.pop(0))
                continue
            # Non-retriable or exhausted retries
            body = (resp.text or "")[:200]
            raise KokoroSynthesisError(f"Kokoro HTTP {resp.status_code} at {url}: {body}")

    def synth(self, task: TTSTask) -> Path:
        voice = (task.voice or "").strip()
        if not voice:
            voice = (self._default_voice or "").strip()
        if not voice:
            raise SynthesisError("Kokoro voice is required but missing (no task.voice and no default)")

        speed = _parse_speed(task.style)
        seed = _parse_seed(task.style)
        payload: dict[str, Any] = {
            "model": "kokoro",
            "voice": voice,
            "input": task.text,
        }
        if speed is not None:
            payload["speed"] = float(speed)
        if seed is not None:
            payload["seed"] = int(seed)

        wav_bytes = self._post_tts(payload)
        # Decode WAV bytes
        try:
            y, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32", always_2d=False)
        except Exception as e:
            raise KokoroSynthesisError(f"Failed to decode Kokoro WAV: {e}") from e
        if y.ndim == 2:
            y = y.mean(axis=1)
        y = np.asarray(y, dtype=np.float32)
        task.out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(task.out_path, y, sr)
        return task.out_path
