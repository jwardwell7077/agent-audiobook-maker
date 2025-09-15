#!/usr/bin/env python3
"""Summarize chapter QC and report ACX pass/fail.

Reads <renders-dir>/manifests/book_manifest.json, loads each chapter QC JSON,
and produces a summary report with per-chapter and aggregate results.

Exit codes:
- 0: All chapters pass ACX checks
- 1: One or more chapters fail ACX checks or no chapters found

Usage:
  python -m scripts.qc_grade --renders-dir data/renders/mvs_smoke4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_manifest(renders_dir: Path) -> dict[str, Any]:
    mf = renders_dir / "manifests" / "book_manifest.json"
    if not mf.exists():
        raise FileNotFoundError(f"book manifest not found: {mf}")
    data: dict[str, Any] = json.loads(mf.read_text(encoding="utf-8"))
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--renders-dir", type=Path, required=True)
    ap.add_argument(
        "--out-path",
        type=Path,
        help=("Optional path to write qc_summary.json; defaults to <renders-dir>/manifests/qc_summary.json"),
    )
    args = ap.parse_args(argv)

    manifest = load_manifest(args.renders_dir)
    chapters = manifest.get("chapters", [])
    if not chapters:
        print("No chapters found in manifest")
        return 1

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    lufs_values: list[float] = []
    peak_values: list[float] = []
    for ch in chapters:
        qc_rel = Path(ch["qc_path"])  # e.g., qc/ch_000.qc.json
        qc_path = args.renders_dir / qc_rel
        qc = json.loads(qc_path.read_text(encoding="utf-8"))
        record = {
            "index": ch.get("index"),
            "title": ch.get("title"),
            "duration_s": qc.get("duration_s"),
            "integrated_lufs": qc.get("integrated_lufs"),
            "peak_dbfs": qc.get("peak_dbfs"),
            "approx_noise_floor_dbfs": qc.get("approx_noise_floor_dbfs"),
            "lufs_ok": qc.get("lufs_ok", False),
            "peak_ok": qc.get("peak_ok", False),
            "noise_ok": qc.get("noise_ok", False),
            "acx_ok": qc.get("acx_ok", False),
            "qc_path": str(qc_rel),
        }
        results.append(record)
        if not record["acx_ok"]:
            failures.append(record)
        lufs = record.get("integrated_lufs")
        if isinstance(lufs, int | float):
            lufs_values.append(float(lufs))
        peak = record.get("peak_dbfs")
        if isinstance(peak, int | float):
            peak_values.append(float(peak))

    summary = {
        "total_chapters": len(results),
        "failed_chapters": len(failures),
        "lufs_min": min(lufs_values) if lufs_values else None,
        "lufs_median": sorted(lufs_values)[len(lufs_values) // 2] if lufs_values else None,
        "lufs_max": max(lufs_values) if lufs_values else None,
        "peak_max_dbfs": max(peak_values) if peak_values else None,
        "chapters": results,
        "failures": failures,
    }

    out_path = args.out_path or (args.renders_dir / "manifests" / "qc_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    # Human summary
    if failures:
        print(f"QC FAIL: {len(failures)}/{len(results)} chapters failed ACX checks. See {out_path}.")
        for f in failures[:10]:
            print(
                f" - ch_{int(f['index']):03d}: lufs_ok={f['lufs_ok']} peak_ok={f['peak_ok']} noise_ok={f['noise_ok']}"
            )
        return 1
    else:
        print(f"QC PASS: {len(results)} chapters passed ACX checks. See {out_path}.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
