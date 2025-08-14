#!/usr/bin/env bash
set -euo pipefail
# Helper to call a saved LangFlow flow via API.
# Usage: FLOW_ID=your_flow_id ./scripts/langflow_curl_example.sh "Your prompt here"

: "${FLOW_ID:?Set FLOW_ID environment variable to the flow id (see Share -> API access)}"
PROMPT=${1:-"hello"}
HOST=${LANGFLOW_HOST:-"http://localhost:7860"}
API_KEY_HEADER=""
if [ -n "${LANGFLOW_API_KEY:-}" ]; then
  API_KEY_HEADER="-H x-api-key:${LANGFLOW_API_KEY}"
fi

cat <<EOF
Calling flow ${FLOW_ID} at ${HOST}
Prompt: ${PROMPT}
EOF

curl -s -X POST "${HOST}/api/v1/run/${FLOW_ID}" \
  -H 'Content-Type: application/json' \
  ${API_KEY_HEADER} \
  -d @<(cat <<JSON
{
  "output_type": "chat",
  "input_type": "chat",
  "input_value": "${PROMPT}",
  "tweaks": {}
}
JSON
)
