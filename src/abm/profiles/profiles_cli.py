"""Command line utilities for profile files."""

# isort: skip_file

# ruff: noqa: I001
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from collections import Counter
from dataclasses import asdict
from pathlib import Path

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore

    HAVE_YAML = True
except Exception:  # pragma: no cover - YAML not installed
    yaml = None  # type: ignore
    HAVE_YAML = False

from abm.profiles import Style, load_profiles, normalize_speaker_name
from abm.voice import pick_voice

__all__ = ["main"]


def _cmd_audit(ns) -> int:
    """Audit profiles against annotation speakers.

    Args:
        ns: Parsed argparse namespace with ``profiles`` and ``annotations`` paths.

    Returns:
        Exit code: ``0`` if all speakers are mapped, ``2`` if any are
        unmapped, ``1`` on IO errors.
    """

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

    decisions = [
        pick_voice(cfg, spk, preferred_engine=ns.prefer_engine)
        for spk in sorted(speakers)
    ]
    unmapped = [
        d.speaker for d in decisions if d.method == "default" and d.reason == "unknown"
    ]
    method_counts = Counter(d.method for d in decisions)
    alias_pct = (
        method_counts.get("alias", 0) / len(decisions) * 100 if decisions else 0.0
    )
    summary = {
        "total": len(decisions),
        "unmapped": unmapped,
        "alias_percent": alias_pct,
        "methods": dict(method_counts),
    }
    if ns.out:
        out_path = Path(ns.out)
        if out_path.suffix == ".json":
            out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        else:
            lines = [
                f"total: {summary['total']}",
                f"unmapped: {len(unmapped)}",
                f"alias%: {alias_pct:.1f}",
            ]
            for m, c in method_counts.items():
                lines.append(f"{m}: {c}")
            out_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        if unmapped:
            print("Unmapped speakers: " + ", ".join(unmapped))
        print(
            f"total={summary['total']} unmapped={len(unmapped)} alias%={alias_pct:.1f}"
        )
    return 2 if unmapped else 0


def _scan_voices(voices_dir: Path | None) -> list[str]:
    """Return available voice IDs from a directory or a small default set."""

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
    """Generate a starter profiles YAML from annotations.

    Args:
        ns: Parsed argparse namespace containing ``annotations`` path and
            output options.

    Returns:
        Exit code ``0`` on success, ``1`` on missing dependencies or IO errors.
    """

    if not HAVE_YAML:
        print(
            "PyYAML required for generate; install with 'pip install pyyaml'",
            file=sys.stderr,
        )
        return 1

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

    narr_norms = {
        normalize_speaker_name("Narrator"),
        normalize_speaker_name("System"),
        normalize_speaker_name("UI"),
    }
    for spk in top:
        if normalize_speaker_name(spk) in narr_norms:
            continue
        speakers[spk] = {"engine": ns.engine, "voice": ""}

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
    out_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the profiles CLI."""

    parser = ArgumentParser(prog="profiles")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="Audit profiles against annotations")
    p_audit.add_argument("--profiles", required=True, type=Path)
    p_audit.add_argument("--annotations", required=True, type=Path)
    p_audit.add_argument("--prefer-engine")
    p_audit.add_argument("--out", type=Path)
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
