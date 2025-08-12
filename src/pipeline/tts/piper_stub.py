from __future__ import annotations
"""Piper TTS stub.

This is a placeholder that simulates TTS synthesis by writing the text to a
.wav-like file (not real audio). Replace with real Piper invocation later.
"""
from pathlib import Path
from typing import Iterable, Any, List
import json


def synthesize_segments_to_stems(
    book_id: str,
    chapter_id: str,
    segments: Iterable[dict | Any],
    out_dir: Path,
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stems: List[Path] = []
    for i, seg in enumerate(segments):
        if isinstance(seg, dict):
            text = seg.get("text", "")
        else:
            text = getattr(seg, "text", "")
        stem_path = out_dir / f"{i:05d}.wav"
        # Placeholder: write JSON metadata not real audio
        stem_path.write_text(
            json.dumps({"text": text}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        stems.append(stem_path)
    return stems


__all__ = ["synthesize_segments_to_stems"]
