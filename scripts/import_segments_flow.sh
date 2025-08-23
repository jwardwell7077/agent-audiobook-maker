#!/usr/bin/env bash
set -euo pipefail

# Ensure repo root
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLOW_JSON="${REPO_ROOT}/examples/langflow/segments_flow_components.json"

if [[ ! -f "$FLOW_JSON" ]]; then
  echo "Flow JSON not found: $FLOW_JSON" >&2
  exit 1
fi

echo "Import this flow in LangFlow UI: $FLOW_JSON"
echo "1) Start LangFlow: ./scripts/run_langflow.sh"
echo "2) In the UI, use 'Import' and select the JSON above."
