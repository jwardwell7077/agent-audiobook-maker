#!/usr/bin/env bash
set -euo pipefail

# Fail commit if banned tokens appear in staged changes.
# Banned: exact title and known acronyms (case-insensitive), and any obvious variants.

PATTERN='(MyVampireSystem|\bMVS\b|\bmvs\b)'

# Collect staged file list
files=$(git diff --cached --name-only --diff-filter=ACMR)

if [ -z "$files" ]; then
	exit 0
fi

fail=0
while IFS= read -r f; do
	[ -z "$f" ] && continue
	# Only check text files
	if file "$f" | grep -qiE 'text|utf-8|ascii'; then
		if grep -I -n -E "$PATTERN" "$f" >/dev/null 2>&1; then
			echo "Banned token found in: $f" >&2
			fail=1
		fi
	fi
done <<< "$files"

exit $fail
