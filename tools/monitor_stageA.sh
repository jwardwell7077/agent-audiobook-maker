#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-run_metrics}"
shift || true
mkdir -p "$OUT_DIR"

# Check deps and print a brief header
cmd_exists() { command -v "$1" >/dev/null 2>&1; }

echo "[mon] writing to $OUT_DIR"

if cmd_exists nvidia-smi; then
  stdbuf -oL nvidia-smi --query-gpu=timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total,clocks.sm,power.draw,temperature.gpu \
    --format=csv -l 1 > "$OUT_DIR/gpu.csv" &
  GPU_MON_PID=$!
else
  echo "[mon] nvidia-smi not found; skipping GPU monitor" | tee -a "$OUT_DIR/monitor.log"
  GPU_MON_PID=""
fi

if cmd_exists mpstat; then
  mpstat -P ALL 1 > "$OUT_DIR/cpu.csv" &
  CPU_MON_PID=$!
else
  echo "[mon] mpstat not found; skipping CPU monitor" | tee -a "$OUT_DIR/monitor.log"
  CPU_MON_PID=""
fi

if cmd_exists iostat; then
  iostat -mx 1 > "$OUT_DIR/io.csv" &
  IO_MON_PID=$!
else
  echo "[mon] iostat not found; skipping disk I/O monitor" | tee -a "$OUT_DIR/monitor.log"
  IO_MON_PID=""
fi

if cmd_exists vmstat; then
  vmstat 1 > "$OUT_DIR/mem.csv" &
  VM_MON_PID=$!
else
  echo "[mon] vmstat not found; skipping memory monitor" | tee -a "$OUT_DIR/monitor.log"
  VM_MON_PID=""
fi

# Run pipeline in foreground (to capture /usr/bin/time -v)
echo "[mon] starting pipeline…"
(
  if cmd_exists /usr/bin/time; then
    /usr/bin/time -v "$@"
  else
    echo "[mon] /usr/bin/time not available; running without it" | tee -a "$OUT_DIR/monitor.log"
    "$@"
  fi
) 2> "$OUT_DIR/time.txt" &
PIPE_PID=$!

# Per-process monitor if pidstat available
if cmd_exists pidstat; then
  pidstat -r -u -d -h -p $PIPE_PID 1 > "$OUT_DIR/pid.csv" &
  PIDSTAT_PID=$!
else
  echo "[mon] pidstat not found; skipping per-process monitor" | tee -a "$OUT_DIR/monitor.log"
  PIDSTAT_PID=""
fi

# Wait for pipeline
wait $PIPE_PID
RET=$?

# Stop monitors
for P in $GPU_MON_PID $CPU_MON_PID $IO_MON_PID $VM_MON_PID ${PIDSTAT_PID:-}; do
  if [[ -n "${P}" ]]; then
    kill "$P" >/dev/null 2>&1 || true
  fi
done

echo "[mon] done, exit=$RET, logs in $OUT_DIR"
exit $RET
