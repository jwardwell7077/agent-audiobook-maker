#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
PID_FILE=".langflow.pid"

if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    kill "$PID" || true
    sleep 1
    if ps -p "$PID" >/dev/null 2>&1; then
      kill -9 "$PID" || true
    fi
    echo "Stopped LangFlow PID=$PID"
  else
    echo "Stale PID in $PID_FILE"
  fi
  rm -f "$PID_FILE"
else
  echo "No PID file found. Attempting best-effort shutdown..."
  pkill -f "langflow run" || true
fi
