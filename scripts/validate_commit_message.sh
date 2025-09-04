#!/usr/bin/env bash
set -euo pipefail

# Validate commit message to enforce exactly one linked issue and a short summary.
# Rules:
# - Subject line max 72 chars
# - Must contain exactly one "Fixes #<number>" (case-insensitive)
# - Optional scope prefix allowed via branch name; message itself should not link multiple issues

MSG_FILE="$1"
msg=$(cat "$MSG_FILE")

subject=$(printf '%s' "$msg" | head -n1)
if [ ${#subject} -gt 72 ]; then
  echo "Commit subject too long (>72 chars): $subject" >&2
  exit 1
fi

# Count issue links of the form Fixes #123 (case-insensitive)
count=$(printf '%s' "$msg" | grep -Eoi '\bfixes #[0-9]+' | wc -l | tr -d ' ')
if [ "$count" -ne 1 ]; then
  echo "Commit must link exactly one issue using 'Fixes #<number>' (found $count)." >&2
  exit 1
fi

exit 0
