#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

NUM_RE = re.compile(r"[-+]?[0-9]*\.?[0-9]+")


def to_float(x: str | None, default: float = math.nan) -> float:
    if x is None:
        return default
    try:
        return float(x)
    except Exception:
        m = NUM_RE.search(x)
        return float(m.group(0)) if m else default


def summarize_gpu(path: Path) -> list[str]:
    if not path.exists():
        return ["- gpu.csv: not found"]
    lines = path.read_text(errors="ignore").splitlines()
    if not lines:
        return ["- gpu.csv: empty"]
    start_i = 1 if lines[0].lower().startswith("timestamp") else 0
    util = []
    mem_util = []
    mem_used = []
    clocks = []
    power = []
    temp = []
    mem_total = None
    for ln in lines[start_i:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 9:
            continue
        util.append(to_float(parts[2]))
        mem_util.append(to_float(parts[3]))
        mu = to_float(parts[4])
        mt = to_float(parts[5])
        mem_used.append(mu)
        if mem_total is None and mt and mt > 0:
            mem_total = mt
        clocks.append(to_float(parts[6]))
        power.append(to_float(parts[7]))
        temp.append(to_float(parts[8]))
    if not util:
        return ["- gpu.csv: no samples"]
    out = [
        f"- GPU util avg/max: {mean(util):.1f}% / {max(util):.1f}%",
        f"- GPU mem used avg/max: {mean(mem_used):.0f}/{max(mem_used):.0f} MiB"
        + (f" of {mem_total:.0f} MiB" if mem_total else ""),
        f"- GPU SM clock avg: {mean(clocks):.0f} MHz | Power avg: {mean(power):.1f} W | Temp avg: {mean(temp):.0f} °C",
    ]
    return out


def summarize_cpu(path: Path) -> list[str]:
    if not path.exists():
        return ["- cpu.csv: not found"]
    lines = path.read_text(errors="ignore").splitlines()
    header_cols: list[str] | None = None
    samples = []
    for ln in lines:
        if not ln or ln.startswith("Linux "):
            continue
        s = ln.strip()
        # Header line can be either "CPU %usr ..." or "<time> CPU %usr ..."
        if (" CPU " in s or s.startswith("CPU ")) and "%usr" in s and "%idle" in s:
            parts = [c for c in re.split(r"\s+", s) if c]
            try:
                cpu_idx = parts.index("CPU")
            except ValueError:
                continue
            header_cols = parts[cpu_idx:]
            continue
        if header_cols is None:
            continue
        parts = [p for p in re.split(r"\s+", s) if p]
        if len(parts) < len(header_cols):
            continue
        # Align from the right to ignore leading timestamp
        row = parts[-len(header_cols) :]
        rec = {header_cols[i]: row[i] for i in range(len(header_cols))}
        cpu_id = rec.get("CPU")
        if cpu_id != "all":
            continue
        samples.append(
            (
                to_float(rec.get("%usr"), 0.0),
                to_float(rec.get("%sys"), 0.0),
                to_float(rec.get("%iowait"), 0.0),
                to_float(rec.get("%idle"), 0.0),
            )
        )
    if not samples:
        return ["- cpu.csv: no 'all' CPU samples parsed"]
    usr = [s[0] for s in samples]
    sys = [s[1] for s in samples]
    iow = [s[2] for s in samples]
    idle = [s[3] for s in samples]
    return [
        f"- CPU usr avg/max: {mean(usr):.1f}% / {max(usr):.1f}%",
        f"- CPU sys avg/max: {mean(sys):.1f}% / {max(sys):.1f}%",
        f"- CPU iowait avg/max: {mean(iow):.2f}% / {max(iow):.2f}%",
        f"- CPU idle avg/min: {mean(idle):.1f}% / {min(idle):.1f}%",
    ]


def summarize_vmstat(path: Path) -> list[str]:
    if not path.exists():
        return ["- mem.csv (vmstat): not found"]
    lines = path.read_text(errors="ignore").splitlines()
    header = None
    vals = []
    for ln in lines:
        if ln.startswith("procs "):
            header = None
            continue
        if ln.strip().startswith("r  b   swpd"):
            header = [c for c in re.split(r"\s+", ln.strip()) if c]
            continue
        if not header:
            continue
        parts = [c for c in re.split(r"\s+", ln.strip()) if c]
        if len(parts) < len(header):
            continue
        rec = {header[i]: parts[i] for i in range(len(header))}
        vals.append(rec)
    if not vals:
        return ["- mem.csv: no samples parsed"]

    def colf(name: str) -> list[float]:
        return [to_float(v.get(name), 0.0) for v in vals]

    free = colf("free")
    cache = colf("cache")
    us = colf("us")
    sy = colf("sy")
    idl = colf("id")
    wa = colf("wa")
    bi = colf("bi")
    bo = colf("bo")
    return [
        f"- Mem free avg/min: {mean(free):.0f} / {min(free):.0f} kB",
        f"- Page cache avg: {mean(cache):.0f} kB",
        f"- CPU from vmstat (us/sy/id/wa) avg: {mean(us):.1f}/{mean(sy):.1f}/{mean(idl):.1f}/{mean(wa):.2f}%",
        f"- Block IO bi/bo avg/max: {mean(bi):.1f}/{mean(bo):.1f} | {max(bi):.0f}/{max(bo):.0f} kB/s",
    ]


def summarize_iostat(path: Path) -> list[str]:
    if not path.exists():
        return ["- io.csv (iostat): not found"]
    lines = path.read_text(errors="ignore").splitlines()
    headers = None
    per_dev: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("Device"):
            headers = [c for c in re.split(r"\s+", ln.strip()) if c]
            i += 1
            while i < len(lines) and lines[i].strip():
                row = [c for c in re.split(r"\s+", lines[i].strip()) if c]
                if len(row) >= len(headers):
                    dev = row[0]
                    rec = {headers[j]: row[j] for j in range(len(headers))}
                    for key in ("rMB/s", "wMB/s", "%util", "r/s", "w/s"):
                        if key in rec:
                            per_dev[dev][key].append(to_float(rec[key], 0.0))
                i += 1
        else:
            i += 1
    if not per_dev:
        return ["- io.csv: no device samples parsed"]
    # Pick top devices by average %util
    dev_stats = []
    for dev, metrics in per_dev.items():
        util_avg = mean(metrics.get("%util", [0.0]))
        rmb = mean(metrics.get("rMB/s", [0.0]))
        wmb = mean(metrics.get("wMB/s", [0.0]))
        dev_stats.append((util_avg, dev, rmb, wmb))
    dev_stats.sort(reverse=True)
    top = dev_stats[:3]
    out = ["- Top I/O devices by %util (avg):"]
    for util_avg, dev, rmb, wmb in top:
        out.append(f"  - {dev}: %util={util_avg:.2f}% rMB/s={rmb:.2f} wMB/s={wmb:.2f}")
    return out


def summarize_pidstat(path: Path) -> list[str]:
    if not path.exists():
        return ["- pid.csv (pidstat): not found"]
    lines = path.read_text(errors="ignore").splitlines()
    header = None
    vals = []
    for ln in lines:
        if not ln or ln.startswith("Linux "):
            continue
        if ln.startswith("# Time"):
            header = [c for c in re.split(r"\s+", ln.strip()) if c and c != "#"]
            continue
        if header is None:
            continue
        parts = [c for c in re.split(r"\s+", ln.strip()) if c]
        if len(parts) < len(header):
            continue
        rec = {header[i]: parts[i] for i in range(len(header))}
        vals.append(rec)
    if not vals:
        return ["- pid.csv: no samples parsed"]

    def colf(name: str) -> list[float]:
        return [to_float(v.get(name), 0.0) for v in vals]

    pcpu = colf("%CPU")
    usr = colf("%usr")
    sysc = colf("%system")
    rss = colf("RSS")
    vsz = colf("VSZ")
    rd = colf("kB_rd/s")
    wr = colf("kB_wr/s")
    return [
        f"- Process %CPU avg/max: {mean(pcpu):.1f}% / {max(pcpu):.1f}% (usr={mean(usr):.1f}% sys={mean(sysc):.1f}%)",
        f"- RSS avg/max: {mean(rss) / 1024:.1f} / {max(rss) / 1024:.1f} MiB | VSZ avg: {mean(vsz) / 1024:.1f} MiB",
        f"- I/O kB/s rd/wr avg: {mean(rd):.1f} / {mean(wr):.1f}",
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize monitor CSV files into markdown")
    ap.add_argument("--mon-dir", required=True, help="Directory containing gpu.csv, cpu.csv, io.csv, mem.csv, pid.csv")
    args = ap.parse_args()

    mon = Path(args.mon_dir)
    out_md = mon / "csv_summaries.md"

    lines: list[str] = []
    lines.append("# Monitor CSV Summaries\n")

    lines.append("## gpu.csv\n")
    lines.extend(summarize_gpu(mon / "gpu.csv"))
    lines.append("")

    lines.append("## cpu.csv (mpstat)\n")
    lines.extend(summarize_cpu(mon / "cpu.csv"))
    lines.append("")

    lines.append("## mem.csv (vmstat)\n")
    lines.extend(summarize_vmstat(mon / "mem.csv"))
    lines.append("")

    lines.append("## io.csv (iostat -mx)\n")
    lines.extend(summarize_iostat(mon / "io.csv"))
    lines.append("")

    lines.append("## pid.csv (pidstat -r -u -d)\n")
    lines.extend(summarize_pidstat(mon / "pid.csv"))
    lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote summaries to {out_md}")


if __name__ == "__main__":
    main()
