"""Render an audiobook chapter from a synthesis script."""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

import soundfile as sf

from abm.audio.assembly import assemble
from abm.audio.engine_registry import EngineRegistry
from abm.audio.mastering import master
from abm.audio.qc_report import qc_report, write_qc_json
from abm.audio.tts_base import TTSTask
from abm.audio.tts_manager import TTSManager

try:  # pragma: no cover - optional dependency
    from pydub.exceptions import CouldntDecodeError
except Exception:  # pragma: no cover
    CouldntDecodeError = None  # type: ignore

__all__ = ["main"]


def _load_script(path: Path) -> tuple[int, str | None, list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return 0, None, data
    index = int(data.get("index") or data.get("chapter_index") or 0)
    title = data.get("title") or data.get("chapter_title")
    items = data.get("items") or data.get("spans") or data.get("segments") or []
    return index, title, items


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``render_chapter`` CLI."""

    parser = argparse.ArgumentParser(prog="render_chapter")
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--tmp-dir", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--lufs", type=float, default=-18.0)
    parser.add_argument("--peak", type=float, default=-3.0)
    parser.add_argument("--crossfade-ms", type=int, default=15)
    parser.add_argument("--engine-workers", type=str, default="{}")
    parser.add_argument(
        "--workers",
        action="append",
        default=[],
        help="Override workers per engine (engine=N). Can be repeated.",
    )
    parser.add_argument(
        "--show-progress", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument(
        "--save-master-wav", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument(
        "--save-mp3", action=argparse.BooleanOptionalAction, default=False
    )
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    tmp_dir: Path = args.tmp_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chapters").mkdir(parents=True, exist_ok=True)
    (out_dir / "qc").mkdir(parents=True, exist_ok=True)
    (out_dir / "manifests").mkdir(parents=True, exist_ok=True)
    spans_dir = tmp_dir / "spans"
    spans_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = tmp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    chapter_index, chapter_title, items = _load_script(args.script)

    tasks: list[TTSTask] = []
    for i, item in enumerate(items):
        out_path = spans_dir / f"c{i:03d}.wav"
        tasks.append(
            TTSTask(
                text=item["text"],
                speaker=item.get("speaker", ""),
                engine=item["engine"],
                voice=item.get("voice"),
                profile_id=item.get("profile_id"),
                refs=item.get("refs", []),
                out_path=out_path,
                pause_ms=int(item.get("pause_ms", 120)),
                style=item.get("style", ""),
            )
        )

    engine_workers = json.loads(args.engine_workers or "{}")
    for w in args.workers:
        if "=" in w:
            eng, n = w.split("=", 1)
            engine_workers[eng] = int(n)
    managers: dict[str, TTSManager] = {}
    grouped: dict[str, list[TTSTask]] = {}
    for task in tasks:
        grouped.setdefault(task.engine, []).append(task)
    for engine, eng_tasks in grouped.items():
        adapter = EngineRegistry.create(engine)
        workers = int(engine_workers.get(engine, 2))
        managers[engine] = TTSManager(
            adapter,
            max_workers=workers,
            cache_dir=cache_dir,
            show_progress=args.show_progress,
        )
        to_render = [t for t in eng_tasks if not t.out_path.exists()]
        if to_render:
            managers[engine].render_batch(to_render)

    span_paths = [t.out_path for t in tasks]
    pauses = [t.pause_ms for t in tasks]
    y, sr = assemble(span_paths, pauses, crossfade_ms=args.crossfade_ms)
    y = master(y, sr, target_lufs=args.lufs, peak_dbfs=args.peak)

    chapter_id = f"ch_{chapter_index:03d}"
    wav_path = out_dir / "chapters" / f"{chapter_id}.wav"
    if args.save_master_wav:
        sf.write(wav_path, y, sr, subtype="PCM_16")

    mp3_path = None
    if args.save_mp3:
        try:  # pragma: no cover - optional dependency
            from pydub import AudioSegment

            mp3_path = out_dir / "chapters" / f"{chapter_id}.mp3"
            AudioSegment.from_wav(str(wav_path)).export(mp3_path, format="mp3")
        except (ImportError, OSError) as exc:  # pragma: no cover
            mp3_path = None
            logging.getLogger(__name__).warning("MP3 export skipped: %s", exc)
        except Exception as exc:  # pragma: no cover
            if CouldntDecodeError is not None and isinstance(exc, CouldntDecodeError):
                mp3_path = None
                logging.getLogger(__name__).warning("MP3 export skipped: %s", exc)
            else:
                raise

    report = qc_report(y, sr)
    qc_path = out_dir / "qc" / f"{chapter_id}.qc.json"
    write_qc_json(report, qc_path)

    manifest_path = out_dir / "manifests" / "book_manifest.json"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"chapters": []}
    manifest["provenance"] = {
        "crossfade_ms": args.crossfade_ms,
        "target_lufs": args.lufs,
        "peak_dbfs": args.peak,
        "engine_workers": engine_workers,
        "cache_dir": str(cache_dir),
    }
    entry = {
        "index": chapter_index,
        "title": chapter_title,
        "wav_path": str(wav_path.relative_to(out_dir)),
        "qc_path": str(qc_path.relative_to(out_dir)),
        "duration_s": report["duration_s"],
        "integrated_lufs": report["integrated_lufs"],
        "peak_dbfs": report["peak_dbfs"],
    }
    if mp3_path:
        entry["mp3_path"] = str(mp3_path.relative_to(out_dir))
    chapters = [
        c for c in manifest.get("chapters", []) if c.get("index") != chapter_index
    ]
    chapters.append(entry)
    chapters.sort(key=lambda c: c["index"])
    manifest["chapters"] = chapters
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(
        f"Wrote {wav_path} ("
        f"{report['duration_s']:.2f}s, {report['integrated_lufs']:.1f} LUFS, "
        f"peak {report['peak_dbfs']:.1f} dBFS)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
