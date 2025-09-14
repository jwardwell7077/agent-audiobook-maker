#!/usr/bin/env bash
set -euo pipefail

BOOK="${1:-private_book}"
BASE="data/ann/${BOOK}"
CLEAN="data/clean/${BOOK}"

mkdir -p "${BASE}" data/.doccache metrics

BNLP_ENABLED="${BNLP_ENABLED:-false}"

echo "[prod-run] Stage A (doc-mode + cache)"
python -m abm.annotate.annotate_cli \
  --in "${CLEAN}/classified/chapters.json" \
  --out-json "${BASE}/combined.json" \
  --out-roster "${BASE}/book_roster.json" \
  --out-dir "${BASE}/chapters" \
  --out-md "${BASE}/review.md" \
  --metrics-jsonl "${BASE}/metrics.jsonl" \
  --status rich \
  --mode high \
  --parse-mode doc \
  --doc-cache data/.doccache \
  --pipe-batch-size 8 \
  --treat-single-as-thought \
  --roster-scope book \
  --verbose

TAGGED_JSON="${BASE}/combined.json"
if [ -f "${BASE}/combined.json" ] && [ "${BNLP_ENABLED}" = "true" ]; then
  echo "[prod-run] Stage A+ (BNLP fuse) [ENABLED]"
  if python -m abm.annotate.bnlp_refine --tagged "${BASE}/combined.json" --out "${BASE}/combined_bnlp.json" --verbose; then
    TAGGED_JSON="${BASE}/combined_bnlp.json"
  else
    echo "[prod-run] BNLP failed; continuing without it"
    TAGGED_JSON="${BASE}/combined.json"
  fi
else
  echo "[prod-run] Stage A+ (BNLP fuse) [DISABLED]"
fi

echo "[prod-run] Stage B (LLM refine)"
python -m abm.annotate.llm_refine \
  --tagged   "${TAGGED_JSON}" \
  --out-json "${BASE}/combined_refined.json" \
  --out-md   "${BASE}/review_refined.md" \
  --endpoint http://127.0.0.1:11434/v1 \
  --model    llama3.1:8b-instruct-q6_K \
  --votes    3 \
  --manage-llm \
  --cache    "${BASE}/llm.cache.sqlite"


echo "[prod-run] Voice casting"
python -m abm.voice.voicecasting_cli \
  --combined     "${BASE}/combined_refined.json" \
  --out-profiles "${BASE}/speaker_profile.json" \
  --out-cast     "${BASE}/casting_plan.json" \
  --top-k 16 --minor-pool 6 \
  --verbose

echo "[prod-run] Done. Outputs under ${BASE}"