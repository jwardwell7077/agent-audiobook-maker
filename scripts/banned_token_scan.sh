#!/usr/bin/env bash
set -euo pipefail
# Only scan for legacy proprietary name; short generic codes allowed internally.
TOKENS_REGEX='SAMPLE_BOOK'
echo "[scan] Checking for banned tokens..."
if git grep -I -n -E "$TOKENS_REGEX" -- ':!logs/*' ':!*.log' ':!*.db' ':!*.egg-info' ':!.venv*' ':!scripts/banned_token_scan.sh' ':!scripts/history_scrub_replace.py' > /tmp/banned_hits.$$ 2>/dev/null; then
  echo "ERROR: Banned tokens detected:"
  cat /tmp/banned_hits.$$
  rm /tmp/banned_hits.$$
  exit 1
fi
rm -f /tmp/banned_hits.$$ || true
echo "[scan] OK - no banned tokens."
