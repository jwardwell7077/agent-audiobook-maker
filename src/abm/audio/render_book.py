"""Orchestrate rendering of an entire audiobook.

This module provides a small CLI wrapper around :mod:`abm.audio.render_chapter`
that iterates over a directory of chapter synthesis scripts.  Each chapter is
rendered in-process which avoids spawning additional Python interpreters.  A
manifest describing the rendered chapters is written to
``<out-dir>/manifests/book_manifest.json``.

The CLI is available as ``python -m abm.audio.render_book``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections.abc import Iterable
from pathlib import Path

from abm.audio.render_chapter import main as render_chapter_main

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _discover_scripts(
    scripts_dir: Path, start: int | None, end: int | None
) -> list[tuple[int, Path, str | None]]:
    """Return ``(index, path, title)`` for scripts within ``scripts_dir``.

    Args:
        scripts_dir: Directory containing ``ch_###.synth.json`` files.
        start: Optional starting chapter index.
        end: Optional ending chapter index.

    Returns:
        Sorted list of discovered scripts with optional titles.
    """

    scripts: list[tuple[int, Path, str | None]] = []
    for path in sorted(scripts_dir.glob("ch_*.synth.json")):
        m = re.search(r"ch_(\d+)\.synth\.json", path.name)
        if not m:
            continue
        idx = int(m.group(1))
        if start is not None and idx < start:
            continue
        if end is not None and idx > end:
            continue
        title: str | None = None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                title = data.get("title") or data.get("chapter_title")
        except Exception:  # pragma: no cover - malformed input
            title = None
        scripts.append((idx, path, title))
    scripts.sort(key=lambda x: x[0])
    return scripts


def _load_qc(qc_path: Path) -> dict:
    """Load a QC report from ``qc_path``.

    Args:
        qc_path: Path to the QC JSON file.

    Returns:
        dict: Parsed QC report.
    """

    with qc_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_entry(
    idx: int, title: str | None, qc: dict, wav_rel: Path, qc_rel: Path
) -> dict:
    """Construct a manifest entry for a single chapter.

    Args:
        idx: Chapter index.
        title: Optional chapter title.
        qc: QC statistics dictionary.
        wav_rel: Path to the WAV file relative to the manifest base.
        qc_rel: Path to the QC file relative to the manifest base.

    Returns:
        dict: Manifest entry for the chapter.
    """

    return {
        "index": idx,
        "title": title,
        "wav_path": str(wav_rel),
        "qc_path": str(qc_rel),
        "duration_s": qc.get("duration_s", 0.0),
        "integrated_lufs": qc.get("integrated_lufs"),
        "peak_dbfs": qc.get("peak_dbfs"),
    }


def _write_manifest(
    manifest_path: Path, base_dir: Path, entries: Iterable[dict]
) -> None:
    """Write ``book_manifest.json`` to ``manifest_path``.

    Args:
        manifest_path: Destination manifest path.
        base_dir: Base directory used for relative paths.
        entries: Iterable of chapter manifest entries.

    Returns:
        None: This function does not return anything.
    """

    manifest = {"base_dir": str(base_dir), "chapters": list(entries)}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``render_book`` CLI.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Process exit code. ``0`` on success, ``1`` if any chapters failed.
    """

    parser = argparse.ArgumentParser(prog="render_book")
    parser.add_argument("--scripts-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--engine-workers", type=str, default="{}")
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument(
        "--resume", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--show-progress", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    out_dir: Path = args.out_dir
    chapters_dir = out_dir / "chapters"
    qc_dir = out_dir / "qc"
    manifests_dir = out_dir / "manifests"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    scripts = _discover_scripts(args.scripts_dir, args.start, args.end)
    if not scripts:
        LOG.warning("No scripts found in %s", args.scripts_dir)

    entries: list[dict] = []
    failures: list[int] = []
    for idx, script_path, title in scripts:
        wav_path = chapters_dir / f"ch_{idx:03d}.wav"
        qc_path = qc_dir / f"ch_{idx:03d}.qc.json"
        wav_rel = wav_path.relative_to(out_dir)
        qc_rel = qc_path.relative_to(out_dir)
        if args.resume and wav_path.exists() and qc_path.exists():
            qc = _load_qc(qc_path)
            LOG.info(
                "Skipping chapter %s%s (resume)",
                idx,
                f" {title!r}" if title else "",
            )
            entries.append(_build_entry(idx, title, qc, wav_rel, qc_rel))
            continue
        argv_ch = [
            "--script",
            str(script_path),
            "--out-dir",
            str(out_dir),
            "--engine-workers",
            args.engine_workers,
        ]
        if not args.show_progress:
            argv_ch.append("--no-show-progress")
        try:
            ret = render_chapter_main(argv_ch)
            if ret != 0:
                raise RuntimeError(f"render_chapter failed for {script_path}")
            qc = _load_qc(qc_path)
            entry = _build_entry(idx, title, qc, wav_rel, qc_rel)
            entries.append(entry)
            LOG.info(
                "Rendered chapter %s%s -> %s; QC -> %s",
                idx,
                f" {title!r}" if title else "",
                entry["wav_path"],
                entry["qc_path"],
            )
        except Exception as exc:  # pragma: no cover - error path
            failures.append(idx)
            LOG.error("Chapter %s failed: %s", idx, exc)
            continue

    manifest_path = manifests_dir / "book_manifest.json"
    _write_manifest(manifest_path, out_dir, entries)

    LOG.info("Rendered %d chapters; %d failed", len(entries), len(failures))
    if failures:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
