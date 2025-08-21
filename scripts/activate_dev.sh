#!/usr/bin/env bash
# Source this to add venv-enforcing wrapper binaries to PATH
+set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${ROOT_DIR}/scripts/dev-bin:${PATH}"
echo "[dev-env] Added scripts/dev-bin to PATH (venv guard active)."
