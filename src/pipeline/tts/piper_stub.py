"""Piper TTS stub.

Placeholder synthesizer that writes per-segment JSON metadata to .wav-like
files (not real audio). Replace with real Piper invocation later.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast


def synthesize_segments_to_stems(
    book_id: str,
    chapter_id: str,
    segments: Iterable[Mapping[str, Any] | Any],
    out_dir: Path,
) -> list[Path]:
    """Write placeholder per-segment stem files and return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stems: list[Path] = []
    for i, seg in enumerate(segments):
        if isinstance(seg, Mapping):
            mseg = cast(Mapping[str, Any], seg)
            text = str(mseg.get("text", ""))
        else:
            text = str(getattr(seg, "text", ""))
        stem_path = out_dir / f"{i:05d}.wav"
        # Placeholder: write JSON metadata not real audio
        stem_path.write_text(
            json.dumps({"text": text}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        stems.append(stem_path)
    return stems


__all__ = ["synthesize_segments_to_stems"]
