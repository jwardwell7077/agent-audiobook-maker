#!/usr/bin/env bash
# Start LangFlow in background on a stable port and write PID
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
PORT=${PORT:-${LANGFLOW_PORT:-7860}}
HOST=${HOST:-${LANGFLOW_HOST:-127.0.0.1}}
COMPONENTS_PATH="${LANGFLOW_COMPONENTS_PATH:-$REPO_ROOT/src/abm/lf_components}"
LOG_FILE="${LANGFLOW_LOG_FILE:-$REPO_ROOT/langflow.run.log}"
PID_FILE=".langflow.pid"

# prevent duplicates
if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "LangFlow already running with PID $(cat "$PID_FILE")"
  exit 0
fi

export PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT:${PYTHONPATH-}"

nohup ./scripts/run_langflow.sh > "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
echo "Started LangFlow PID=$PID at http://$HOST:$PORT"
