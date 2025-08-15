#!/usr/bin/env bash
set -euo pipefail
# Only scan for legacy proprietary name; represented via hex to avoid
# accidental copy/paste or simplistic text scans in history tooling.
LEGACY_FULL_HEX='4d7956616d7069726553797374656d'
TOKENS_REGEX="$(printf '%s' "$LEGACY_FULL_HEX" | xxd -r -p)"
echo "[scan] Checking for banned tokens..."
if git grep -I -n -E "$TOKENS_REGEX" -- ':!logs/*' ':!*.log' ':!*.db' ':!*.egg-info' ':!.venv*' ':!scripts/banned_token_scan.sh' ':!scripts/history_scrub_replace.py' > /tmp/banned_hits.$$ 2>/dev/null; then
  echo "ERROR: Banned tokens detected:"
  cat /tmp/banned_hits.$$
  rm /tmp/banned_hits.$$
  exit 1
fi
rm -f /tmp/banned_hits.$$ || true
echo "[scan] OK - no banned tokens."
