from __future__ import annotations

# isort: skip_file

import base64
import io
import os
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
import soundfile as sf  # type: ignore[import-untyped]


class KokoroSynthesisError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Cfg:
    url: str
    timeout_s: int


class KokoroEngine:
    def __init__(self, url: str | None = None, timeout_s: int = 90):
        base = (url or os.getenv("KOKORO_URL") or "http://127.0.0.1:8880").rstrip("/")
        self.endpoint = f"{base}/v1/audio/speech"
        self.cfg = _Cfg(url=base, timeout_s=int(timeout_s))
        # Reuse HTTP connections for performance under concurrency
        pool_size = int(os.getenv("KOKORO_HTTP_POOL", "32"))
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        self._session = session

    def _decode_audio(self, resp: requests.Response) -> tuple[NDArray[np.float32], int]:
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "audio" in ctype or "octet-stream" in ctype:
            # Try decode as raw audio bytes first; if libsndfile fails, fall back to JSON-with-base64
            raw = resp.content or b""
            if not raw:
                raise KokoroSynthesisError("Empty audio response bytes")
            buf = io.BytesIO(raw)
            try:
                audio, sr = sf.read(buf, dtype="float32", always_2d=False)
            except Exception:
                # Some servers mislabel JSON as audio; attempt JSON parse fallback
                try:
                    payload = resp.json()
                except Exception as exc:
                    preview = resp.content[:200]
                    try:
                        preview = preview.decode("utf-8", errors="ignore")
                    except Exception:
                        preview = str(preview)
                    raise KokoroSynthesisError(
                        f"Invalid audio bytes and JSON parse failed: {resp.status_code} preview={preview}"
                    ) from exc
                b64 = payload.get("audio") or payload.get("wav_base64")
                if not b64:
                    raise KokoroSynthesisError(f"Missing audio in JSON: {list(payload.keys())}") from None
                b64s = str(b64)
                if b64s.startswith("data:"):
                    b64s = b64s.split(",", 1)[-1]
                buf = io.BytesIO(base64.b64decode(b64s))
                audio, sr = sf.read(buf, dtype="float32", always_2d=False)
        else:
            try:
                payload = resp.json()
            except Exception as exc:
                raise KokoroSynthesisError(f"Unexpected response: {resp.status_code} {resp.text[:200]}") from exc
            b64 = payload.get("audio") or payload.get("wav_base64")
            if not b64:
                raise KokoroSynthesisError(f"Missing audio in JSON: {list(payload.keys())}")
            b64s = str(b64)
            if b64s.startswith("data:"):
                b64s = b64s.split(",", 1)[-1]
            buf = io.BytesIO(base64.b64decode(b64s))
            audio, sr = sf.read(buf, dtype="float32", always_2d=False)
        if audio.ndim == 2:
            audio = audio.mean(axis=1)
        return audio.astype(np.float32, copy=False), int(sr)

    def synthesize_to_array(
        self, text: str, voice_id: str | None, speed: float | None = None, seed: int | None = None
    ) -> tuple[NDArray[np.float32], int]:
        if not voice_id:
            raise KokoroSynthesisError("voice_id is required for Kokoro")
        body: dict[str, Any] = {"model": "kokoro", "voice": voice_id, "input": text, "format": "wav"}
        if speed is not None:
            body["speed"] = float(speed)
        if seed is not None:
            body["seed"] = int(seed)
        backoffs = [0.5, 1.0, 2.0]
        last = ""
        # Allow a single retry with a safe default if the server reports an unknown voice
        fallback_attempted = False
        for delay in [0.0] + backoffs:
            if delay:
                time.sleep(delay)
            try:
                r = self._session.post(
                    self.endpoint,
                    json=body,
                    timeout=self.cfg.timeout_s,
                    headers={"Accept": "audio/wav, application/json"},
                )
            except requests.RequestException as e:
                last = f"request failed: {e}"
                continue
            if r.status_code == 200:
                try:
                    return self._decode_audio(r)
                except KokoroSynthesisError as e:
                    # treat as transient and retry with backoff
                    last = f"decode failed: {e}"
                    continue
            # If validation error due to unknown voice, swap to a safe default once
            if r.status_code == 400 and not fallback_attempted:
                try:
                    payload = r.json()
                    detail = payload.get("detail") if isinstance(payload, dict) else None
                    message = None
                    if isinstance(detail, dict):
                        message = detail.get("message")
                    if not message and isinstance(payload, dict):
                        message = payload.get("message")
                except Exception:
                    message = None
                msg = str(message or "")
                if "not found" in msg.lower() and "voice" in msg.lower():
                    # Use a common built-in voice to maximize success; prefer male for 'Victor'
                    orig_voice = str(body.get("voice") or "")
                    body["voice"] = "am_michael" if orig_voice.lower() == "victor" else "af_bella"
                    fallback_attempted = True
                    last = f"400 unknown voice '{orig_voice}', retrying with {body['voice']}"
                    continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"{r.status_code} {r.text[:160]}"
                continue
            raise KokoroSynthesisError(f"{r.status_code} {r.text[:200]}")
        raise KokoroSynthesisError(f"Failed after retries: {last}")
