"""Command line utilities for profile files."""

# ruff: noqa: I001
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from abm.profiles.character_profiles import (
    Style,
    _resolve_with_reason,
    load_profiles,
    normalize_speaker_name,
)

__all__ = ["main"]


def _cmd_audit(ns) -> int:
    """Audit profiles against annotation speakers."""

    try:
        cfg = load_profiles(ns.profiles)
    except Exception as exc:  # pragma: no cover - IO errors
        print(f"failed to load profiles: {exc}", file=sys.stderr)
        return 1
    try:
        data = json.loads(Path(ns.annotations).read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - IO errors
        print(f"failed to load annotations: {exc}", file=sys.stderr)
        return 1

    speakers: set[str] = set()
    for ch in data.get("chapters", []):
        for span in ch.get("spans", []):
            if span.get("type") in {"Dialogue", "Thought", "Narration"}:
                spk = span.get("speaker")
                if spk:
                    speakers.add(spk)

    unmapped: list[str] = []
    alias_hits = 0
    fallback_hits = 0
    for spk in sorted(speakers):
        prof, reason = _resolve_with_reason(cfg, spk)
        if prof is None:
            unmapped.append(spk)
        else:
            if reason == "alias":
                alias_hits += 1
            if ns.prefer_engine and ns.prefer_engine in prof.fallback:
                fallback_hits += 1

    if unmapped:
        print("Unmapped speakers: " + ", ".join(unmapped))
    total = len(speakers)
    alias_pct = (alias_hits / total * 100) if total else 0.0
    summary = f"total={total} unmapped={len(unmapped)} alias%={alias_pct:.1f}"
    if ns.prefer_engine:
        summary += f" fallback.{ns.prefer_engine}={fallback_hits}"
    print(summary)
    return 2 if unmapped else 0


def _scan_voices(voices_dir: Path | None) -> list[str]:
    voices = (
        [p.name for p in voices_dir.iterdir()]
        if voices_dir and voices_dir.exists()
        else []
    )
    voices = sorted(set(voices))
    if not voices:
        voices = ["en_US/ryan-high", "en_US/lessac-medium", "en_GB/callan-medium"]
    return voices


def _cmd_generate(ns) -> int:
    """Generate a starter profiles YAML from annotations."""

    try:
        data = json.loads(Path(ns.annotations).read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - IO errors
        print(f"failed to load annotations: {exc}", file=sys.stderr)
        return 1

    counts: Counter[str] = Counter()
    for ch in data.get("chapters", []):
        for span in ch.get("spans", []):
            if span.get("type") in {"Dialogue", "Thought", "Narration"}:
                spk = span.get("speaker")
                if spk:
                    counts[spk] += 1

    top = [s for s, _ in counts.most_common(ns.n_top)]
    voice_ids = _scan_voices(Path(ns.voices_dir) if ns.voices_dir else None)
    narrator_voice = voice_ids[0]
    speakers: dict[str, dict[str, str]] = {
        "Narrator": {"engine": ns.engine, "voice": narrator_voice}
    }

    idx = 1
    narr_norms = {
        normalize_speaker_name("Narrator"),
        normalize_speaker_name("System"),
        normalize_speaker_name("UI"),
    }
    for spk in top:
        if normalize_speaker_name(spk) in narr_norms:
            continue
        voice = voice_ids[idx % len(voice_ids)]
        if voice == narrator_voice and len(voice_ids) > 1:
            idx += 1
            voice = voice_ids[idx % len(voice_ids)]
        speakers[spk] = {"engine": ns.engine, "voice": voice}
        idx += 1

    cfg = {
        "version": 1,
        "defaults": {
            "engine": ns.engine,
            "narrator_voice": narrator_voice,
            "style": asdict(Style()),
        },
        "voices": {ns.engine: voice_ids},
        "speakers": speakers,
    }
    out_path = Path(ns.out)
    try:
        import yaml  # type: ignore

        out_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    except Exception:  # pragma: no cover - YAML missing
        out_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the profiles CLI."""

    parser = ArgumentParser(prog="profiles")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="Audit profiles against annotations")
    p_audit.add_argument("--profiles", required=True, type=Path)
    p_audit.add_argument("--annotations", required=True, type=Path)
    p_audit.add_argument("--prefer-engine")
    p_audit.set_defaults(func=_cmd_audit)

    p_gen = sub.add_parser(
        "generate", help="Generate starter profiles from annotations"
    )
    p_gen.add_argument("--annotations", required=True, type=Path)
    p_gen.add_argument("--out", required=True, type=Path)
    p_gen.add_argument("--engine", default="piper")
    p_gen.add_argument("--voices-dir")
    p_gen.add_argument("--n-top", type=int, default=12)
    p_gen.set_defaults(func=_cmd_generate)

    ns = parser.parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
