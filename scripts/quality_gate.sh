#!/usr/bin/env bash
set -euo pipefail

start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "QUALITY GATE START ${start}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src"
VENV_BIN="${ROOT_DIR}/.venv/bin"

run() { echo -e "\n== $1 =="; shift; "$@"; }

run "Ruff Format" "${VENV_BIN}/ruff" format "${SRC_DIR}"
run "Ruff Fix"    "${VENV_BIN}/ruff" check --fix "${SRC_DIR}"
run "Pyright"     "${VENV_BIN}/pyright"
run "Mypy"        "${VENV_BIN}/mypy" "${SRC_DIR}"
run "Pydoclint"   "${VENV_BIN}/pydoclint" "${SRC_DIR}"
run "Interrogate" "${VENV_BIN}/interrogate" -c "${ROOT_DIR}/pyproject.toml" "${SRC_DIR}"
run "Pytest"      env PYTHONPATH="${SRC_DIR}:tests" "${VENV_BIN}/pytest" -vv

end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo -e "\nQUALITY GATE COMPLETE ✅ ${end}"
