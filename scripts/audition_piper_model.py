#!/usr/bin/env python3
"""Audition a Piper model/voice with standard phrases.

Usage examples:
  - By voice id installed under Piper voices dir:
      ./scripts/audition_piper_model.py en_US-ryan-medium

  - By direct ONNX path (expects a sibling .json or .onnx.json config):
      ./scripts/audition_piper_model.py /path/to/en_US-ryan-medium.onnx

Optional env vars:
  - ABM_PIPER_BIN: Path to the piper binary (defaults to 'piper')
  - ABM_AUDITIONS_DIR: Output root (default: data/voices/auditions)
  - ABM_PIPER_DRYRUN=1: Generate short silence WAVs (useful for CI)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

from abm.audio.piper_adapter import PiperAdapter
from abm.audio.tts_base import TTSTask


DEFAULT_PHRASES = [
    "The quick brown fox jumps over the lazy dog.",
    "She sells seashells by the seashore.",
    "In the beginning, there was only darkness.",
    "Chapter One: A Strange Discovery.",
    "Numbers: zero one two three four five six seven eight nine.",
    "Punctuation test — dashes, ellipses… quotes “like this”.",
    "Proper nouns: Quinn, Vorden, Layla Munrow, Brad Richardson.",
]


def _slugify(text: str) -> str:
    import re

    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "voice"


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audition a Piper model/voice with sample phrases")
    p.add_argument(
        "voice",
        help="Piper voice id (e.g., en_US-ryan-medium) or path to a .onnx model file",
    )
    p.add_argument(
        "--out",
        dest="out_dir",
        default=os.environ.get("ABM_AUDITIONS_DIR", "data/voices/auditions"),
        help="Output directory root (default: data/voices/auditions)",
    )
    p.add_argument(
        "--phrases",
        dest="phrases_file",
        help="Optional text file with one phrase per line (overrides defaults)",
    )
    p.add_argument(
        "--prefix",
        dest="prefix",
        default=None,
        help="Optional filename prefix (default uses voice/model slug)",
    )
    return p.parse_args(argv)


def load_phrases(phrases_file: str | None) -> list[str]:
    if not phrases_file:
        return DEFAULT_PHRASES
    path = Path(phrases_file)
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    return [ln for ln in lines if ln]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    phrases = load_phrases(args.phrases_file)

    voice = args.voice
    slug = _slugify(Path(voice).stem if voice.endswith(".onnx") else voice)
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / f"{slug}-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    adapter = PiperAdapter(voice=None)
    adapter.preload()

    print(f"[audition] voice={voice} -> {out_dir}")
    failures = 0
    for i, text in enumerate(phrases, start=1):
        idx = f"{i:02d}"
        wav_path = out_dir / f"{idx}-{_slugify(text)[:40] or 'sample'}.wav"
        task = TTSTask(
            text=text,
            speaker="Audition",
            engine="piper",
            voice=voice,
            profile_id=None,
            refs=[],
            out_path=wav_path,
            pause_ms=0,
            style="audition",
        )
        try:
            adapter.synth(task)
            print(f"  ✓ {wav_path}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  ✗ failed: {wav_path} -> {e}")

    print(f"[audition] done: {len(phrases)-failures} succeeded, {failures} failed")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
