#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in repo root
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Load environment variables from .env file if it exists
if [[ -f ".env" ]]; then
  echo "[run_langflow] Loading configuration from .env file..."
  # Export variables from .env, ignoring comments and empty lines
  set -a
  source .env
  set +a
fi

# Enforce venv if available
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Make local components importable (abm.lf_components and lf_components/*)
export PYTHONPATH="${REPO_ROOT}/src:${REPO_ROOT}:${PYTHONPATH-}"

# Ensure the local package is installed (editable) for abm.* imports
python - <<'PY'
try:
    import abm  # noqa: F401
    print("[run_langflow] abm package available.")
except Exception:
    import sys, subprocess
    print("[run_langflow] Installing local package in editable mode...", flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])  # installs agent-audiobook-maker
PY

if ! command -v langflow >/dev/null 2>&1; then
  echo "LangFlow is not installed in this environment."
  echo "Install with: pip install langflow"
  exit 1
fi

PORT=${PORT:-${LANGFLOW_PORT:-7860}}
HOST=${HOST:-${LANGFLOW_HOST:-127.0.0.1}}

# LangFlow custom components path (auto-discovery in the UI)
# Use .env value if set, otherwise fall back to default
DEFAULT_COMPONENTS_PATH="${REPO_ROOT}/src/abm/lf_components"
COMPONENTS_PATH="${LANGFLOW_COMPONENTS_PATH:-$DEFAULT_COMPONENTS_PATH}"

# Ensure LANGFLOW_COMPONENTS_PATH is exported for LangFlow's auto-discovery
export LANGFLOW_COMPONENTS_PATH="$COMPONENTS_PATH"

LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')
# If DEBUG_MODE is true, force debug logging
if [[ "${DEBUG_MODE:-false}" == "true" ]]; then
  LOG_LEVEL_LOWER="debug"
fi

# Log file path (default to repo root)
LOG_FILE_PATH="${LANGFLOW_LOG_FILE:-${REPO_ROOT}/langflow.log}"

echo "Launching LangFlow with components on http://${HOST}:${PORT}"
echo " - Python path: ${PYTHONPATH}"
echo " - Components path: ${COMPONENTS_PATH}"
echo " - LANGFLOW_COMPONENTS_PATH: ${LANGFLOW_COMPONENTS_PATH}"
echo " - Log level: ${LOG_LEVEL_LOWER}"
echo " - Log file: ${LOG_FILE_PATH}"
echo " - Import from 'abm.lf_components' or use auto-discovered custom components."

# Show a quick inventory of custom components directory for debugging
if [[ -d "$COMPONENTS_PATH" ]]; then
  echo "[run_langflow] Components directory tree (one level):"
  find "$COMPONENTS_PATH" -maxdepth 2 -type f -name "*.py" -printf "  %P\n" | sort || true
fi

if [[ -d "$COMPONENTS_PATH" ]]; then
  if [[ "${DEBUG_MODE:-false}" == "true" ]]; then
    exec env LANGFLOW_COMPONENTS_PATH="$LANGFLOW_COMPONENTS_PATH" \
      langflow run --host "$HOST" --port "$PORT" \
      --components-path "$COMPONENTS_PATH" \
      --log-level "$LOG_LEVEL_LOWER" --log-file "$LOG_FILE_PATH" --dev
  else
    exec env LANGFLOW_COMPONENTS_PATH="$LANGFLOW_COMPONENTS_PATH" \
      langflow run --host "$HOST" --port "$PORT" \
      --components-path "$COMPONENTS_PATH" \
      --log-level "$LOG_LEVEL_LOWER" --log-file "$LOG_FILE_PATH"
  fi
else
  echo "[run_langflow] Components path not found: $COMPONENTS_PATH (continuing without --components-path)" >&2
  if [[ "${DEBUG_MODE:-false}" == "true" ]]; then
    exec langflow run --host "$HOST" --port "$PORT" \
      --log-level "$LOG_LEVEL_LOWER" --log-file "$LOG_FILE_PATH" --dev
  else
    exec langflow run --host "$HOST" --port "$PORT" \
      --log-level "$LOG_LEVEL_LOWER" --log-file "$LOG_FILE_PATH"
  fi
fi
