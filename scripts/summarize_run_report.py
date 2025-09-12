#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean


def parse_time_txt(path: Path) -> dict[str, str | float]:
    out: dict[str, str | float] = {}
    if not path.exists():
        return out
    txt = path.read_text(errors="ignore")
    # Parse key lines from /usr/bin/time -v
    for line in txt.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    # Normalize elapsed seconds if possible (format H:MM:SS)
    el = out.get("Elapsed (wall clock) time")
    if isinstance(el, str):
        parts = el.split(":")
        try:
            if len(parts) == 3:
                h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
                out["elapsed_sec"] = h * 3600 + m * 60 + s
            elif len(parts) == 2:
                m, s = int(parts[0]), float(parts[1])
                out["elapsed_sec"] = m * 60 + s
        except Exception:
            pass
    return out


_NUM_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+")


def parse_gpu_csv(path: Path) -> dict[str, float | int | None]:
    # Columns requested in monitor_stageA.sh:
    # timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total,clocks.sm,power.draw,temperature.gpu
    if not path.exists():
        return {}
    util = []
    mem_util = []
    mem_used = []
    mem_total = None
    clocks = []
    power = []
    temp = []
    lines = path.read_text(errors="ignore").splitlines()
    # Skip header if present
    start_i = 1 if lines and lines[0].lower().startswith("timestamp") else 0
    for ln in lines[start_i:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 9:
            continue

        # Extract numeric values robustly (strip units)
        def num(s: str) -> float:
            m = _NUM_RE.search(s)
            return float(m.group(0)) if m else math.nan

        util.append(num(parts[2]))
        mem_util.append(num(parts[3]))
        mu = num(parts[4])
        mt = num(parts[5])
        mem_used.append(mu)
        if not mem_total and mt > 0:
            mem_total = mt
        clocks.append(num(parts[6]))
        power.append(num(parts[7]))
        temp.append(num(parts[8]))
    if not util:
        return {}
    return {
        "gpu_util_avg": round(mean(x for x in util if not math.isnan(x)), 2),
        "gpu_util_max": round(max(util), 2),
        "gpu_mem_util_avg": round(mean(x for x in mem_util if not math.isnan(x)), 2),
        "gpu_mem_used_avg_mib": round(mean(x for x in mem_used if not math.isnan(x)), 2),
        "gpu_mem_used_max_mib": round(max(mem_used), 2),
        "gpu_mem_total_mib": mem_total,
        "gpu_sm_clock_avg_mhz": round(mean(x for x in clocks if not math.isnan(x)), 2),
        "gpu_power_avg_w": round(mean(x for x in power if not math.isnan(x)), 2),
        "gpu_temp_avg_c": round(mean(x for x in temp if not math.isnan(x)), 2),
    }


def parse_metrics_jsonl(path: Path) -> tuple[list[dict[str, object]], dict[str, float | int]]:
    rows: list[dict[str, object]] = []
    agg: dict[str, float | int] = {
        "chapters": 0,
        "spans_total": 0,
        "unknown_speakers": 0,
        "time_normalize": 0.0,
        "time_roster": 0.0,
        "time_segment": 0.0,
        "time_attribute": 0.0,
        "time_total_sum": 0.0,
    }
    if not path.exists():
        return rows, agg
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            rows.append(rec)
            agg["chapters"] += 1
            agg["spans_total"] += int(rec.get("spans_total") or 0)
            agg["unknown_speakers"] += int(rec.get("unknown_speakers") or 0)
            agg["time_normalize"] += float(rec.get("time_normalize") or 0.0)
            agg["time_roster"] += float(rec.get("time_roster") or 0.0)
            agg["time_segment"] += float(rec.get("time_segment") or 0.0)
            agg["time_attribute"] += float(rec.get("time_attribute") or 0.0)
            agg["time_total_sum"] += float(rec.get("time_total") or 0.0)
    return rows, agg


def load_combined(path: Path) -> tuple[int, int, Counter[str]]:
    if not path.exists():
        return 0, 0, Counter[str]()
    doc = json.loads(path.read_text())
    total = 0
    unknown = 0
    methods: Counter[str] = Counter()
    for ch in doc.get("chapters", []):
        for s in ch.get("spans", []):
            if s.get("type") in {"Dialogue", "Thought"}:
                total += 1
                if s.get("speaker") == "Unknown":
                    unknown += 1
                methods[s.get("method") or "?"] += 1
    return total, unknown, methods


def load_book_roster(path: Path) -> int:
    if not path.exists():
        return 0
    r = json.loads(path.read_text())
    return sum(len(v) for v in r.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize monitored run and chapter metrics")
    ap.add_argument("--mon-dir", required=True, help="Directory with monitor logs (gpu.csv, time.txt, etc.)")
    ap.add_argument("--out-dir", required=True, help="Annotation output dir with metrics.jsonl/combined.json")
    args = ap.parse_args()

    mon = Path(args.mon_dir)
    outd = Path(args.out_dir)

    time_info = parse_time_txt(mon / "time.txt")
    gpu_info = parse_gpu_csv(mon / "gpu.csv")
    rows, agg = parse_metrics_jsonl(outd / "metrics.jsonl")
    total_spans, unknown_spans, methods = load_combined(outd / "combined.json")
    n_entities = load_book_roster(outd / "book_roster.json")

    # Estimates
    elapsed = float(time_info.get("elapsed_sec") or 0.0)
    per_chapters_sum = agg.get("time_total_sum", 0.0)
    init_and_finalize = max(0.0, float(elapsed) - float(per_chapters_sum)) if elapsed else None

    # Averages
    chapters = agg.get("chapters", 0) or 1
    avg_norm = agg["time_normalize"] / chapters
    avg_ros = agg["time_roster"] / chapters
    avg_seg = agg["time_segment"] / chapters
    avg_att = agg["time_attribute"] / chapters
    spans_per_sec = (total_spans / per_chapters_sum) if per_chapters_sum else 0.0

    report_lines = []
    report_lines.append("# Stage A Run Report\n")
    report_lines.append(f"Monitor dir: `{mon}`  |  Output dir: `{outd}`\n")

    # Overall
    report_lines.append("## Overall\n")
    if elapsed:
        report_lines.append(f"- Wall time: {elapsed:.1f}s")
    if per_chapters_sum:
        report_lines.append(f"- Sum per-chapter time: {per_chapters_sum:.1f}s")
    if init_and_finalize is not None:
        report_lines.append(f"- Init + book roster (est.) + finalization: {init_and_finalize:.1f}s")
    report_lines.append(f"- Chapters processed: {agg['chapters']}")
    report_lines.append(f"- Spans (Dialogue/Thought): {total_spans}")
    unk_pct = (unknown_spans / total_spans * 100.0) if total_spans else 0.0
    report_lines.append(f"- Unknown speakers: {unknown_spans} ({unk_pct:.2f}%)")
    report_lines.append(f"- Book roster entities: {n_entities}")
    report_lines.append(f"- Throughput: {spans_per_sec:.2f} spans/sec (chapter phases only)\n")

    # GPU summary
    if gpu_info:
        report_lines.append("## GPU\n")
        util_avg = float(gpu_info.get("gpu_util_avg") or 0.0)
        util_max = float(gpu_info.get("gpu_util_max") or 0.0)
        mem_used_avg = float(gpu_info.get("gpu_mem_used_avg_mib") or 0.0)
        mem_used_max = float(gpu_info.get("gpu_mem_used_max_mib") or 0.0)
        mem_total = float(gpu_info.get("gpu_mem_total_mib") or 0.0) if gpu_info.get("gpu_mem_total_mib") else None
        sm_clock_avg = float(gpu_info.get("gpu_sm_clock_avg_mhz") or 0.0)
        power_avg = float(gpu_info.get("gpu_power_avg_w") or 0.0)
        temp_avg = float(gpu_info.get("gpu_temp_avg_c") or 0.0)

        report_lines.append(f"- Utilization avg/max: {util_avg:.1f}% / {util_max:.1f}%")
        if mem_total:
            report_lines.append(f"- Memory avg/max: {mem_used_avg:.0f}/{mem_used_max:.0f} MiB of {mem_total:.0f} MiB")
        report_lines.append(
            f"- SM clock avg: {sm_clock_avg:.0f} MHz | Power avg: {power_avg:.1f} W | Temp avg: {temp_avg:.0f} °C"
        )
        report_lines.append("")

    # Stage timing summary
    report_lines.append("## Stage timings\n")
    report_lines.append(
        "- Average per chapter: "
        f"normalize={avg_norm:.3f}s, roster={avg_ros:.3f}s, "
        f"segment={avg_seg:.3f}s, attribute={avg_att:.3f}s"
    )

    # Top slow chapters by attribute time
    def safe_float(x: object, default: float = 0.0) -> float:
        if x is None:
            return default
        if isinstance(x, float):
            return x
        if isinstance(x, int):
            return float(x)
        if isinstance(x, str):
            try:
                return float(x)
            except Exception:
                return default
        try:
            return float(str(x))
        except Exception:
            return default

    def safe_int(x: object, default: int = 0) -> int:
        if x is None:
            return default
        if isinstance(x, int):
            return x
        if isinstance(x, float):
            return int(x)
        if isinstance(x, str):
            try:
                return int(float(x)) if ("." in x) else int(x)
            except Exception:
                return default
        try:
            s = str(x)
            return int(float(s)) if ("." in s) else int(s)
        except Exception:
            return default

    slow = sorted(rows, key=lambda r: safe_float(r.get("time_attribute")), reverse=True)[:10]
    if slow:
        report_lines.append("- Slowest 10 chapters by attribute time:")
        for r in slow:
            ch_idx = safe_int(r.get("chapter_index"))
            t_att = safe_float(r.get("time_attribute"))
            t_tot = safe_float(r.get("time_total"))
            spans = safe_int(r.get("spans_total"))
            report_lines.append(f"  - ch {ch_idx}: attribute={t_att:.2f}s total={t_tot:.2f}s spans={spans}")
    report_lines.append("")

    # Method distribution
    report_lines.append("## Method distribution (Dialogue/Thought)\n")
    for k, c in methods.most_common(8):
        report_lines.append(f"- {k}: {c}")
    report_lines.append("")

    # Recommendations
    recs = [
        (
            "Ensure GPU stays utilized >50%: if low but CPU high, spaCy may be CPU-bound in tokenization—"
            "consider batching chapters or reducing Python overhead."
        ),
        (
            "Coref is active; if attribute time dominates, consider toggling coref off for shorter chapters or "
            "adding a heuristic to skip when no pronouns nearby."
        ),
        ("If IO is high (not shown here), place data on SSD and avoid writing per-chapter JSON in very verbose mode."),
        (
            "Keep the neighbor-bounded attribution; only revisit clamps after we review this report across multiple "
            "books to avoid overfitting."
        ),
    ]
    report_lines.append("## Recommendations\n")
    report_lines.extend(f"- {rec_line}" for rec_line in recs)

    (mon / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report written to {mon / 'report.md'}")


if __name__ == "__main__":
    main()
