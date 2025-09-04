#!/usr/bin/env bash
set -euo pipefail

echo "Running local pre-push checks..."
if [ -d .venv ]; then
  source .venv/bin/activate
fi

echo "> ruff format --check"
ruff format --check .
echo "> ruff check"
ruff check .
echo "> mypy (src + tests)"
mypy --strict src tests || true
echo "> pytest (quick)"
pytest -q tests/unit_tests

echo "All pre-push checks completed"
