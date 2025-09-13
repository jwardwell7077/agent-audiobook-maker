"""Export per-chapter synthesis scripts from annotated chapters."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from abm.audio.tts_casting import spans_to_tasks
from abm.profiles.character_profiles import CharacterProfilesDB

__all__ = ["main"]


def _parse_only(spec: str | None) -> set[int]:
    if not spec:
        return set()
    result: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            result.update(range(int(start), int(end) + 1))
        else:
            result.add(int(part))
    return result


def _write_summary(out_path: Path, tasks: list[dict]) -> None:
    counts = Counter(t["speaker"] for t in tasks)
    lines = ["# Summary", ""]
    for speaker, n in sorted(counts.items()):
        lines.append(f"- {speaker}: {n}")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``synthesis_export`` CLI."""

    parser = argparse.ArgumentParser(prog="synthesis_export")
    parser.add_argument("--tagged", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--only")
    parser.add_argument("--default-engine", default="piper")
    parser.add_argument("--default-pause", type=int, default=120)
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    scripts_dir = out_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    db = CharacterProfilesDB.load(args.profiles)
    with args.tagged.open("r", encoding="utf-8") as f:
        chapters = json.load(f)

    selected = _parse_only(args.only)
    manifest_path = out_dir / "synth_manifest.json"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"chapters": []}

    for chapter in chapters:
        idx = int(chapter.get("index") or chapter.get("chapter_index") or 0)
        if selected and idx not in selected:
            continue
        spans = chapter.get("spans", [])
        tasks = spans_to_tasks(
            spans,
            db,
            default_engine=args.default_engine,
            default_pause_ms=args.default_pause,
        )
        script_path = scripts_dir / f"ch_{idx:03d}.synth.json"
        with script_path.open("w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        _write_summary(scripts_dir / f"ch_{idx:03d}.summary.md", tasks)
        manifest["chapters"].append({"index": idx, "script": str(script_path)})

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
