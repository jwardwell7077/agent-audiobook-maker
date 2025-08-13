#!/usr/bin/env bash
# Fails if any python file still imports using 'from src.' or 'import src.' style.
set -euo pipefail
if grep -R "from src\." -n src tests || grep -R "import src" -n src tests; then
  echo "Error: 'src' prefix imports detected. Please remove them." >&2
  exit 1
fi
echo "No src.* imports found."
