#!/usr/bin/env bash
set -euo pipefail

# Bootstrap GitHub labels, milestones, and basic project wiring via gh CLI.
# Prereqs: gh auth login; repo permissions; jq installed.

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required. Install from https://cli.github.com/" >&2
  exit 1
fi

REPO=${REPO:-"jwardwell7077/agent-audiobook-maker"}
BOARD_URL=${BOARD_URL:-"https://github.com/users/jwardwell7077/projects/3"}

echo "Repo: $REPO"
echo "Project board: $BOARD_URL"

OWNER="${REPO%/*}"
NAME="${REPO#*/}"

create_label() {
  local name="$1" color="$2" desc="$3"
  # Try to fetch label; create if missing
  if ! gh api -X GET \
    "/repos/${OWNER}/${NAME}/labels/${name}" \
    -H "Accept: application/vnd.github+json" >/dev/null 2>&1; then
    gh api -X POST \
      "/repos/${OWNER}/${NAME}/labels" \
      -H "Accept: application/vnd.github+json" \
      -f name="$name" \
      -f color="$color" \
      -f description="$desc" >/dev/null || true
  fi
}

echo "Creating labels..."
create_label "type:feature" "1f883d" "Feature work"
create_label "type:bug" "d73a4a" "Bug fix"
create_label "type:infra" "a2eeef" "Infra / CI / tooling"
create_label "type:doc" "0e8a16" "Documentation"
create_label "agent-task" "5319e7" "Agent-executable task"
create_label "blocked" "b60205" "Blocked by dependency"
create_label "prio:high" "b60205" "High priority"
create_label "prio:med" "dbab09" "Medium priority"
create_label "prio:low" "c2e0c6" "Low priority"
create_label "scope:ingestion" "0052cc" "Ingestion pipeline scope"
create_label "scope:langflow" "0052aa" "LangFlow components scope"
create_label "scope:tests" "005277" "Tests/fixtures scope"
create_label "scope:docs" "1d76db" "Docs scope"
create_label "scope:infra" "5319e7" "Infra/CI scope"

echo "Creating milestones..."
for ms in "v0.1 KISS" "v0.2 Casting & SSML" "v0.3 TTS + E2E Demo"; do
  # Check if milestone with this title exists
  if ! gh api -X GET \
    "/repos/${OWNER}/${NAME}/milestones?state=all" \
    -H "Accept: application/vnd.github+json" \
    -q ".[].title" | grep -Fxq "$ms"; then
    gh api -X POST \
      "/repos/${OWNER}/${NAME}/milestones" \
      -H "Accept: application/vnd.github+json" \
      -f title="$ms" >/dev/null || true
  fi
done

echo "Done. Configure project auto-add via Settings > Projects or use a GitHub workflow."
