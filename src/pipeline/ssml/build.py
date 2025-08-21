"""SSML generation helpers.

Minimal stub that wraps plain text segments into basic <speak> tags and
injects a voice name mapping per speaker.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SegmentProtocol(Protocol):  # minimal structural segment
    text: str
    speaker: str | None  # may be absent / None


def build_ssml(
    segments: Iterable[Mapping[str, Any] | SegmentProtocol | Any],
    speaker_voice_map: Mapping[str, str] | None = None,
) -> str:
    """Return SSML string for segments with optional speaker->voice map."""
    speaker_voice_map = speaker_voice_map or {}
    parts: list[str] = ["<speak>"]
    for seg in segments:
        if isinstance(seg, Mapping):
            from typing import cast as _cast  # local import to limit scope

            speaker = _cast(str | None, seg.get("speaker"))
            text = _cast(str, seg.get("text", ""))
        else:
            speaker = getattr(seg, "speaker", None)
            text = getattr(seg, "text", "")
        speaker_key: str = "" if speaker is None else f"{speaker}"
        text_str: str = f"{text}"
        voice: str = speaker_voice_map.get(speaker_key, "default")
        safe: str = html.escape(text_str)
        if speaker:
            parts.append(f'<voice name="{voice}">{safe}</voice>')
        else:
            parts.append(str(safe))
    parts.append("</speak>")
    return "".join(parts)


__all__ = ["build_ssml"]
