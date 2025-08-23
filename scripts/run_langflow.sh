#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in repo root
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

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

PORT=${PORT:-7860}
HOST=${HOST:-127.0.0.1}

# LangFlow custom components path (auto-discovery in the UI)
# Override with LANGFLOW_COMPONENTS_PATH env; defaults to repo lf_components
DEFAULT_COMPONENTS_PATH="${REPO_ROOT}/lf_components"
COMPONENTS_PATH="${LANGFLOW_COMPONENTS_PATH:-$DEFAULT_COMPONENTS_PATH}"

echo "Launching LangFlow with components on http://${HOST}:${PORT}"
echo " - Python path: ${PYTHONPATH}"
echo " - Components path: ${COMPONENTS_PATH}"
echo " - Import from 'abm.lf_components' or use auto-discovered custom components."

# Show a quick inventory of custom components directory for debugging
if [[ -d "$COMPONENTS_PATH" ]]; then
  echo "[run_langflow] Components directory tree (one level):"
  find "$COMPONENTS_PATH" -maxdepth 2 -type f -name "*.py" -printf "  %P\n" | sort || true
fi

if [[ -d "$COMPONENTS_PATH" ]]; then
  exec langflow run --host "$HOST" --port "$PORT" \
    --components-path "$COMPONENTS_PATH" \
    --log-level debug --dev --no-open-browser
else
  echo "[run_langflow] Components path not found: $COMPONENTS_PATH (continuing without --components-path)" >&2
  exec langflow run --host "$HOST" --port "$PORT" \
    --log-level debug --dev --no-open-browser
fi
