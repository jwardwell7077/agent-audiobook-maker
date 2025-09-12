#!/usr/bin/env python3
"""
Lightweight monitoring fallback that samples system and process metrics from /proc.
Writes CSV files into the given output directory at a fixed sampling interval.

Outputs:
  cpu.csv  -> timestamp, user, nice, system, idle, iowait, irq, softirq, steal
  mem.csv  -> timestamp, mem_total_kb, mem_free_kb, mem_avail_kb, buffers_kb, cached_kb, swap_total_kb, swap_free_kb
  io.csv   -> timestamp, rd_sectors, wr_sectors, rd_bytes, wr_bytes (best-effort sum over main disks)
  pid.csv  -> timestamp, rss_kb, utime_ticks, stime_ticks, threads, rd_bytes, wr_bytes (for target PID)

Notes:
  - CPU fields are deltas computed between samples.
  - Disk stats are cumulative; bytes approximated (Linux 512-byte sectors typical; try to detect).
  - If /proc/<pid>/io is unavailable, per-process IO will be zero.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path


def read_proc_stat_cpu() -> tuple[str, list[int]]:
    with open("/proc/stat") as f:
        for line in f:
            if line.startswith("cpu "):
                parts = line.split()
                # cpu user nice system idle iowait irq softirq steal guest guest_nice
                vals = list(map(int, parts[1:11]))
                return parts[0], vals
    raise RuntimeError("/proc/stat missing 'cpu' line")


def read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            num = v.strip().split()[0]
            try:
                out[k] = int(num)  # kB units
            except ValueError:
                continue
    return out


def list_main_disks() -> list[str]:
    # Heuristic: include sd[a-z], nvme[0-9]n[0-9]
    names: list[str] = []
    with open("/proc/diskstats") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 14:
                continue
            name = parts[2]
            if name.startswith("sd") and len(name) == 3 and name[2].isalpha():
                names.append(name)
            elif name.startswith("nvme") and "n" in name and "p" not in name:
                names.append(name)
    return names


def read_diskstats(filter_names: set[str]) -> tuple[int, int]:
    # Returns (rd_sectors, wr_sectors)
    rd = 0
    wr = 0
    with open("/proc/diskstats") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 14:
                continue
            name = parts[2]
            if name not in filter_names:
                continue
            # fields per https://www.kernel.org/doc/Documentation/block/stat.txt
            #  6: read sectors, 10: written sectors
            try:
                rd += int(parts[5])
                wr += int(parts[9])
            except Exception:
                pass
    return rd, wr


def read_pid_stat(pid: int) -> tuple[int, int, int, int]:
    # Returns (rss_kb, utime_ticks, stime_ticks, threads)
    with open(f"/proc/{pid}/stat") as f:
        s = f.read()
    # stat has spaces but comm can include spaces within parentheses; find last ')'
    rparen = s.rfind(")")
    rest = s[rparen + 2 :].split()
    # utime=14, stime=15, num_threads=20, rss=24 (1-based after comm)
    utime = int(rest[13 - 1])
    stime = int(rest[14 - 1])
    threads = int(rest[20 - 1])
    rss_pages = int(rest[24 - 1])
    page_kb = os.sysconf("SC_PAGE_SIZE") // 1024
    rss_kb = rss_pages * page_kb
    return rss_kb, utime, stime, threads


def read_pid_io(pid: int) -> tuple[int, int]:
    # Returns (read_bytes, write_bytes) best-effort
    try:
        with open(f"/proc/{pid}/io") as f:
            rd = 0
            wr = 0
            for line in f:
                if line.startswith("read_bytes:"):
                    rd = int(line.split()[1])
                elif line.startswith("write_bytes:"):
                    wr = int(line.split()[1])
            return rd, wr
    except Exception:
        return 0, 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("pid", type=int)
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Initialize CPU baseline
    _, cpu0 = read_proc_stat_cpu()

    # Initialize disk baseline
    disks = set(list_main_disks())
    rd0, wr0 = read_diskstats(disks) if disks else (0, 0)
    # Sector size heuristic (512 default)
    sector_bytes = 512

    # Open files
    cpu_f = (out / "cpu.csv").open("a", buffering=1)
    mem_f = (out / "mem.csv").open("a", buffering=1)
    io_f = (out / "io.csv").open("a", buffering=1)
    pid_f = (out / "pid.csv").open("a", buffering=1)

    # Write headers if empty
    if cpu_f.tell() == 0:
        cpu_f.write("ts,user,nice,system,idle,iowait,irq,softirq,steal\n")
    if mem_f.tell() == 0:
        mem_f.write("ts,mem_total_kb,mem_free_kb,mem_avail_kb,buffers_kb,cached_kb,swap_total_kb,swap_free_kb\n")
    if io_f.tell() == 0:
        io_f.write("ts,rd_sectors,wr_sectors,rd_bytes,wr_bytes\n")
    if pid_f.tell() == 0:
        pid_f.write("ts,rss_kb,utime_ticks,stime_ticks,threads,rd_bytes,wr_bytes\n")

    try:
        while True:
            ts = time.time()

            # CPU
            _, cpu1 = read_proc_stat_cpu()
            delta = [b - a for a, b in zip(cpu0, cpu1, strict=False)]
            # user nice system idle iowait irq softirq steal guest guest_nice
            user, nice, system, idle, iowait, irq, softirq, steal = delta[:8]
            cpu_f.write(f"{ts:.3f},{user},{nice},{system},{idle},{iowait},{irq},{softirq},{steal}\n")
            cpu0 = cpu1

            # Memory
            mem = read_meminfo()
            mem_f.write(
                f"{ts:.3f},{mem.get('MemTotal', 0)},{mem.get('MemFree', 0)},{mem.get('MemAvailable', 0)},"
                f"{mem.get('Buffers', 0)},{mem.get('Cached', 0)},{mem.get('SwapTotal', 0)},{mem.get('SwapFree', 0)}\n"
            )

            # Disk
            if disks:
                rd1, wr1 = read_diskstats(disks)
                io_f.write(f"{ts:.3f},{rd1},{wr1},{(rd1 * sector_bytes)},{(wr1 * sector_bytes)}\n")

            # Per-process (best-effort)
            if os.path.exists(f"/proc/{args.pid}"):
                rss_kb, ut, st, th = read_pid_stat(args.pid)
                rd_b, wr_b = read_pid_io(args.pid)
                pid_f.write(f"{ts:.3f},{rss_kb},{ut},{st},{th},{rd_b},{wr_b}\n")
            else:
                # process ended
                break

            time.sleep(args.interval)
    finally:
        for f in (cpu_f, mem_f, io_f, pid_f):
            try:
                f.flush()
                f.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
