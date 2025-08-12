from __future__ import annotations
"""SSML generation helpers.

Minimal stub that wraps plain text segments into basic <speak> tags and
injects a voice name mapping per speaker.
"""
from typing import Iterable, Any, Dict, List
import html


def build_ssml(
    segments: Iterable[dict | Any],
    speaker_voice_map: Dict[str, str] | None = None,
) -> str:
    speaker_voice_map = speaker_voice_map or {}
    parts: List[str] = ["<speak>"]
    for seg in segments:
        if isinstance(seg, dict):
            speaker = seg.get("speaker")
            text = seg.get("text", "")
        else:
            speaker = getattr(seg, "speaker", None)
            text = getattr(seg, "text", "")
        voice = speaker_voice_map.get(speaker or "", "default")
        safe = html.escape(text)
        if speaker:
            parts.append(f'<voice name="{voice}">{safe}</voice>')
        else:
            parts.append(safe)
    parts.append("</speak>")
    return "".join(parts)


__all__ = ["build_ssml"]
