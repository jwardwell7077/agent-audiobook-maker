#!/usr/bin/env bash
set -euo pipefail

# Fail commit if banned tokens appear in staged changes.
# Construct banned tokens without storing them literally in the repo.

tok_title=$(printf '\x4d\x79\x56\x61\x6d\x70\x69\x72\x65\x53\x79\x73\x74\x65\x6d')
tok_acr_up=$(printf '\x4d\x56\x53')
tok_acr_lo=$(printf '\x6d\x76\x73')

PATTERN="(${tok_title}|\\b${tok_acr_up}\\b|\\b${tok_acr_lo}\\b)"

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
