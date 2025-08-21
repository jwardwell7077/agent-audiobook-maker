#!/usr/bin/env bash
set -euo pipefail

# KISS venv guard: ensure the local .venv is active
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "[venv-guard] Please activate the local .venv (source .venv/bin/activate)" >&2
  exit 1
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="$project_root/.venv"
if [[ "$VIRTUAL_ENV" != "$venv_path" ]]; then
  echo "[venv-guard] Wrong virtualenv. Expected $venv_path but VIRTUAL_ENV=$VIRTUAL_ENV" >&2
  exit 1
fi
