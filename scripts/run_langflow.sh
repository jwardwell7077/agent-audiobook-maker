#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in repo root
cd "$(dirname "$0")/.."

# Enforce venv if available
if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
fi

if ! command -v langflow >/dev/null 2>&1; then
  echo "LangFlow is not installed in this environment."
  echo "Install with: pip install langflow"
  exit 1
fi

PORT=${PORT:-7860}
HOST=${HOST:-127.0.0.1}

exec langflow run --host "$HOST" --port "$PORT"
