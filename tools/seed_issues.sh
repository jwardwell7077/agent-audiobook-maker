#!/usr/bin/env bash
set -euo pipefail

# Seed initial backlog issues with labels and milestone using gh CLI.

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required. Install from https://cli.github.com/" >&2
  exit 1
fi

REPO=${REPO:-"jwardwell7077/agent-audiobook-maker"}
MILESTONE=${MILESTONE:-"v0.1 KISS"}

create_issue() {
  local title="$1" body="$2" labels="$3"
  gh api \
    -X POST \
    -H "Accept: application/vnd.github+json" \
    "/repos/${REPO}/issues" \
    -f title="$title" \
    -f body="$body" \
    -f labels="$(printf '%s' "$labels")" \
    -f milestone="$MILESTONE" >/dev/null || true
}

echo "Seeding backlog issues to $REPO (milestone: $MILESTONE)"

create_issue \
  "Docs: remove legacy two-agent references site-wide" \
  "Scope: Remove or move to docs/_deprecated any remaining legacy multi-agent references.\nAcceptance: link check and markdown lint pass; no broken links from README/docs." \
  "type:doc,scope:docs,prio:med"

create_issue \
  "Docs: KISS quickstart refresh (remove LangFlow)" \
  "Scope: Ensure KISS.md reflects local venv.\nAcceptance: verified steps on Python 3.11." \
  "type:doc,scope:docs,prio:med"

create_issue \
  "CI: add workflow + component smoke test" \
  "Scope: CI on 3.11/3.12 with pre-commit + pytest; include component import smoke.\nAcceptance: CI green on PR." \
  "type:infra,scope:infra,prio:high"

create_issue \
  "Makefile: dev_setup / test_quick targets (remove LangFlow)" \
  "Scope: standardize make targets for quick dev; remove deprecated LangFlow targets.\nAcceptance: commands documented and runnable." \
  "type:infra,scope:infra,prio:low"

create_issue \
  "Casting design note stub (future)" \
  "Scope: add a stub doc for casting/SSML design; no code change.\nAcceptance: doc exists under docs/02-specifications/components." \
  "type:doc,scope:docs,prio:low"

echo "Backlog seeding complete."
