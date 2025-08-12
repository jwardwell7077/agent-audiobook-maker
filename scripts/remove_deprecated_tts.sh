#!/usr/bin/env bash
set -euo pipefail

FILES=(
  "src/tts/engines_impl.py"
  "src/pipeline/tts/engines.py"
)

echo "Checking files..."
TO_DELETE=()
for f in "${FILES[@]}"; do
  if [[ -f "$f" ]]; then
    echo "Will delete: $f"
    TO_DELETE+=("$f")
  else
    echo "Missing (skipped): $f"
  fi
done

if [[ ${#TO_DELETE[@]} -eq 0 ]]; then
  echo "Nothing to remove"; exit 0; fi

read -r -p "Proceed with git removal? [y/N] " ans
if [[ ${ans:-} =~ ^[Yy]$ ]]; then
  git rm "${TO_DELETE[@]}"
  git commit -m "chore: remove deprecated TTS engine shim files"
  echo "Removed and committed."
else
  echo "Aborted."
fi
