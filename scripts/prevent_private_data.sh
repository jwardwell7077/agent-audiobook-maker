#!/usr/bin/env bash
set -euo pipefail

# Block committing non-public data and common media/binary artifacts.
# Also block reports/ outputs.
# Allowed exceptions: data/books/SAMPLE_BOOK/** and its derived SAMPLE_BOOK dirs.

# Build allowlist regex for SAMPLE_BOOK paths
ALLOW_RE='^(data/(books|clean|annotations|renders|stems)/SAMPLE_BOOK(/|$))'

# Forbidden patterns (case-insensitive) for media/binaries and data/
FORBIDDEN_EXT='\.(pdf|mp3|wav|ogg|flac|m4a|m4b|zip|7z|tar|tar\.gz|tgz|bin|dat|pickle|pkl)$'

# Gather staged files
STAGED=$(git diff --cached --name-only --diff-filter=ACMR)

fail=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # Skip deletions or non-existent (renames already handled by diff-filter)
  if [ ! -e "$f" ]; then
    continue
  fi
  # If under data/ and not in SAMPLE_BOOK allowlist, block
  if [[ "$f" == data/* ]] && ! [[ "$f" =~ $ALLOW_RE ]]; then
    echo "Blocked: committing to data/ outside SAMPLE_BOOK is not allowed: $f" >&2
    fail=1
    continue
  fi
  # Block reports/ entirely (evaluation artifacts)
  if [[ "$f" == reports/* ]]; then
    echo "Blocked: committing reports/ artifacts is not allowed: $f" >&2
    fail=1
    continue
  fi
  # If matches forbidden media/binary ext and not allowlisted, block
  shopt -s nocasematch || true
  if [[ "$f" =~ $FORBIDDEN_EXT ]] && ! [[ "$f" =~ $ALLOW_RE ]]; then
    echo "Blocked: committing media/binary artifact: $f" >&2
    fail=1
    continue
  fi
  shopt -u nocasematch || true
  # Prevent run_logs anywhere
  if [[ "$f" == *run_logs/* ]]; then
    echo "Blocked: committing run_logs artifacts is not allowed: $f" >&2
    fail=1
    continue
  fi
  # Prevent files over 20MB unless allowlisted
  size=$(stat -c%s "$f" 2>/dev/null || echo 0)
  if [ "$size" -ge 20971520 ] && ! [[ "$f" =~ $ALLOW_RE ]]; then
    echo "Blocked: file exceeds 20MB: $f ($size bytes)" >&2
    fail=1
    continue
  fi

done <<< "$STAGED"

exit $fail
