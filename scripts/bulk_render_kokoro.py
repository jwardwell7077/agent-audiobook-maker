#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
from pathlib import Path
from typing import Any

PLANS_DIR_DEFAULT = Path("tmp/data/ann/mvs/plans")
RENDERS_DIR_DEFAULT = Path("tmp/renders/mvs")


def _plan_index(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return -1
    if isinstance(data, list):
        try:
            return int(path.stem.split("_")[1])
        except Exception:
            return -1
    try:
        return int(data.get("index") or data.get("chapter_index") or 0)
    except Exception:
        return 0


def _render_one(
    plan_path: Path,
    out_dir: Path,
    *,
    crossfade_ms: int,
    lufs: float,
    peak: float,
    engine_workers: dict[str, int],
    show_progress: bool,
    save_master_wav: bool,
    save_mp3: bool,
) -> tuple[Path, int]:
    from abm.audio.render_chapter import main as render_chapter_main

    argv = [
        "--script",
        str(plan_path),
        "--out-dir",
        str(out_dir),
        "--crossfade-ms",
        str(crossfade_ms),
        "--lufs",
        str(lufs),
        "--peak",
        str(peak),
        "--engine-workers",
        json.dumps(engine_workers),
    ]
    if show_progress:
        argv.append("--show-progress")
    if save_master_wav:
        argv.append("--save-master-wav")
    if save_mp3:
        argv.append("--save-mp3")
    code = render_chapter_main(argv)
    return plan_path, code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bulk render Kokoro plans to chapters")
    ap.add_argument("--plans-dir", type=Path, default=PLANS_DIR_DEFAULT)
    ap.add_argument("--renders-dir", type=Path, default=RENDERS_DIR_DEFAULT)
    ap.add_argument("--pattern", type=str, default="ch_*.json")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 8)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--prefer-engine", type=str, default="kokoro")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--continue-on-error", action="store_true")
    ap.add_argument("--crossfade-ms", type=int, default=15)
    ap.add_argument("--lufs", type=float, default=-18.0)
    ap.add_argument("--peak", type=float, default=-3.0)
    ap.add_argument(
        "--engine-workers-json",
        type=str,
        default="{}",
        help='Per-engine workers mapping, e.g. {"kokoro": 2}',
    )
    args = ap.parse_args(argv)

    plans = sorted(args.plans_dir.glob(args.pattern))
    if not plans:
        print(f"No plans matched in {args.plans_dir} ({args.pattern})")
        return 1

    out_dir: Path = args.renders_dir
    (out_dir / "chapters").mkdir(parents=True, exist_ok=True)
    (out_dir / "qc").mkdir(parents=True, exist_ok=True)
    (out_dir / "manifests").mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(os.environ.get("ABM_TMP_DIR", "tmp")) / "spans"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        engine_workers = json.loads(args.engine_workers_json or "{}")
    except Exception:
        engine_workers = {}
    engine_workers.setdefault("kokoro", 2)

    todo: list[Path] = []
    for p in plans:
        idx = _plan_index(p)
        ch_wav = out_dir / "chapters" / f"ch_{idx:03d}.wav"
        if args.resume and ch_wav.exists():
            if args.verbose:
                print(f"SKIP {p.name} (exists)")
            continue
        todo.append(p)

    if not todo:
        print("Nothing to do.")
        return 0

    print(f"Rendering {len(todo)} chapters with {args.workers} workers → {out_dir}")
    errors: list[tuple[Path, Any]] = []
    completed = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [
            ex.submit(
                _render_one,
                plan,
                out_dir,
                crossfade_ms=args.crossfade_ms,
                lufs=args.lufs,
                peak=args.peak,
                engine_workers=engine_workers,
                show_progress=args.verbose,
                save_master_wav=True,
                save_mp3=False,
            )
            for plan in todo
        ]
        for fut in cf.as_completed(futs):
            try:
                plan_done, code = fut.result()
                completed += 1
                if args.verbose:
                    print(f"DONE {plan_done.name} (code={code}) [{completed}/{len(todo)}]")
            except Exception as exc:
                errors.append((Path("?"), exc))
                if not args.continue_on_error:
                    break

    if errors:
        print(f"Completed with {len(errors)} errors:")
        for p, e in errors[:10]:
            print(f"  {p}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
