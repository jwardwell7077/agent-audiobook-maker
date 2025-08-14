#!/usr/bin/env bash
set -euo pipefail

# Launch LangFlow with project components and tee output to a timestamped log file.
# Allows extra args to be passed through to `langflow run`.
#
# Usage:
#   ./scripts/run_langflow.sh                # start with defaults
#   ./scripts/run_langflow.sh --port 9000     # override port
#   LANGFLOW_COMPONENTS_PATH=custom ./scripts/run_langflow.sh
#
# Environment overrides:
#   LANGFLOW_COMPONENTS_PATH  Path to components (default: <repo>/lf_components)
#   LANGFLOW_HOST              Host bind (default: 0.0.0.0)
#   LANGFLOW_PORT              Port (default: 7860)
#   LANGFLOW_LOG_DIR           Log directory (default: <repo>/logs/langflow)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

LANGFLOW_COMPONENTS_PATH="${LANGFLOW_COMPONENTS_PATH:-${ROOT_DIR}/lf_components}"
LANGFLOW_HOST="${LANGFLOW_HOST:-0.0.0.0}"
LANGFLOW_PORT="${LANGFLOW_PORT:-7860}"
LANGFLOW_LOG_DIR="${LANGFLOW_LOG_DIR:-${ROOT_DIR}/logs/langflow}" 
mkdir -p "${LANGFLOW_LOG_DIR}"

timestamp() { date +%Y-%m-%dT%H:%M:%S; }

LOG_FILE="${LANGFLOW_LOG_DIR}/langflow_$(date +%Y%m%d_%H%M%S).log"

echo "[$(timestamp)] LangFlow launch script starting" | tee -a "${LOG_FILE}"
echo "[$(timestamp)] Components: ${LANGFLOW_COMPONENTS_PATH}" | tee -a "${LOG_FILE}"
echo "[$(timestamp)] Host:Port  : ${LANGFLOW_HOST}:${LANGFLOW_PORT}" | tee -a "${LOG_FILE}"
echo "[$(timestamp)] Log file   : ${LOG_FILE}" | tee -a "${LOG_FILE}"

if ! command -v langflow >/dev/null 2>&1; then
  echo "[ERROR] 'langflow' executable not found in PATH. Install via 'pip install langflow'" | tee -a "${LOG_FILE}"
  exit 1
fi

if [ ! -d "${LANGFLOW_COMPONENTS_PATH}" ]; then
  echo "[ERROR] Components path does not exist: ${LANGFLOW_COMPONENTS_PATH}" | tee -a "${LOG_FILE}"
  exit 1
fi

echo "[$(timestamp)] Starting LangFlow..." | tee -a "${LOG_FILE}"
echo "---------- LANGFLOW STDOUT/STDERR (tee) ----------" | tee -a "${LOG_FILE}"

# Run LangFlow (foreground) so Ctrl+C stops it; logs captured.
LANGFLOW_CMD=(langflow run \
  --host "${LANGFLOW_HOST}" \
  --port "${LANGFLOW_PORT}" \
  --components-path "${LANGFLOW_COMPONENTS_PATH}" \
  "$@")

echo "[$(timestamp)] Command: ${LANGFLOW_CMD[*]}" | tee -a "${LOG_FILE}"

"${LANGFLOW_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"

exit_code=${PIPESTATUS[0]}
echo "[$(timestamp)] LangFlow exited with code ${exit_code}" | tee -a "${LOG_FILE}"
exit ${exit_code}
