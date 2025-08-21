#!/usr/bin/env bash
# Enforce usage of the project-local virtual environment (.venv).
# Fails if commands are executed with a global python outside CI.
set -euo pipefail

if [[ "${ALLOW_SYSTEM_PY:-}" = "1" ]]; then
  exit 0
fi

if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  exit 0
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_VENV="${PROJECT_ROOT}/.venv"

if [[ ! -d "${EXPECTED_VENV}" ]]; then
  echo "[venv-guard] Missing .venv. Run: make install_dev" >&2
  exit 1
fi

if [[ "${VIRTUAL_ENV:-}" != "${EXPECTED_VENV}" ]]; then
  echo "[venv-guard] VIRTUAL_ENV not set to project .venv (expected ${EXPECTED_VENV})." >&2
  echo "Activate with: source .venv/bin/activate" >&2
  exit 1
fi

exit 0
