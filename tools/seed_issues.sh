#!/usr/bin/env bash
set -euo pipefail

# Seed initial backlog issues with labels and milestone using gh CLI.

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required. Install from https://cli.github.com/" >&2
  exit 1
fi

REPO=${REPO:-"jwardwell7077/agent-audiobook-maker"}
MILESTONE=${MILESTONE:-"v0.1 KISS"}

new_issue() {
  local title="$1" body="$2" labels="$3"
  gh issue create -R "$REPO" \
    --title "$title" \
    --body "$body" \
    --label $labels \
    --milestone "$MILESTONE"
}

echo "Seeding backlog issues to $REPO (milestone: $MILESTONE)"

new_issue \
  "Docs: remove legacy two-agent references site-wide" \
  "Scope: Remove or move to docs/_deprecated any remaining legacy multi-agent references.\nAcceptance: link check and markdown lint pass; no broken links from README/docs." \
  "type:doc,scope:docs,prio:med"

new_issue \
  "Docs: KISS quickstart + LangFlow how-to refresh" \
  "Scope: Ensure KISS.md and LangFlow docs reflect local venv, LANGFLOW_COMPONENTS_PATH, and sample flow import.\nAcceptance: verified steps on Python 3.11." \
  "type:doc,scope:docs,prio:med"

new_issue \
  "CI: add workflow + LangFlow smoke test" \
  "Scope: CI on 3.11/3.12 with pre-commit + pytest; include component import smoke.\nAcceptance: CI green on PR." \
  "type:infra,scope:infra,prio:high"

new_issue \
  "Makefile: dev_setup / test_quick / langflow targets" \
  "Scope: add or standardize make targets for quick dev.\nAcceptance: commands documented and runnable." \
  "type:infra,scope:infra,prio:low"

new_issue \
  "Casting design note stub (future)" \
  "Scope: add a stub doc for casting/SSML design; no code change.\nAcceptance: doc exists under docs/02-specifications/components." \
  "type:doc,scope:docs,prio:low"

echo "Backlog seeding complete."
