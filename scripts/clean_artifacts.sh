#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/clean_artifacts.sh <book> [--what=classified|ingest|all] [--dry-run=true|false]

Safely remove generated artifacts under data/clean/<book>.

Options:
  --what=classified   Remove only classifier outputs (data/clean/<book>/classified)
  --what=ingest       Remove only ingest outputs (*.txt, *_meta.json, *.jsonl)
  --what=all          Remove both ingest and classifier outputs
  --dry-run=true      Show what would be removed without deleting

Examples:
  bash scripts/clean_artifacts.sh private_book --what=classified
  bash scripts/clean_artifacts.sh private_book --what=all --dry-run=false
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" || $# -lt 1 ]]; then
  usage
  exit 0
fi

BOOK="$1"; shift || true
WHAT="classified"
DRY_RUN="true"

# Parse flags
for arg in "$@"; do
  case "$arg" in
    --what=*) WHAT="${arg#*=}" ;;
    --dry-run=*) DRY_RUN="${arg#*=}" ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

# Guard: book must be simple token
if [[ ! "$BOOK" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "Refusing to operate on invalid book id: '$BOOK'" >&2
  exit 2
fi

BASE="data/clean/$BOOK"
if [[ ! -d "$BASE" ]]; then
  echo "Directory not found: $BASE" >&2
  exit 1
fi

say() { echo -e "$*"; }

# Build delete lists
declare -a paths
if [[ "$WHAT" == "classified" || "$WHAT" == "all" ]]; then
  paths+=("$BASE/classified")
fi
if [[ "$WHAT" == "ingest" || "$WHAT" == "all" ]]; then
  paths+=(
    "$BASE"/*_raw.txt
    "$BASE"/*_well_done.txt
    "$BASE"/*_ingest_meta.json
    "$BASE"/*_well_done.jsonl
    "$BASE"/*_well_done_meta.json
  )
fi

say "Cleaning artifacts in: $BASE"
say "Mode: $WHAT | Dry-run: $DRY_RUN"

shopt -s nullglob

declare -a to_delete
for p in "${paths[@]}"; do
  for e in $p; do
    [[ -e "$e" ]] && to_delete+=("$e")
  done
done

if (( ${#to_delete[@]} == 0 )); then
  say "Nothing to delete."
  exit 0
fi

say "Items to delete ("${#to_delete[@]}" entries):"
for e in "${to_delete[@]}"; do
  echo "  - $e"
  if [[ "$DRY_RUN" == "false" ]]; then
    rm -rf -- "$e"
  fi
done

if [[ "$DRY_RUN" == "true" ]]; then
  say "Dry-run complete. Re-run with --dry-run=false to apply."
else
  say "Deletion complete."
fi
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/clean_artifacts.sh <book> [--what=classified|ingest|all] [--dry-run=true|false]

Safely remove generated artifacts under data/clean/<book>.

Options:
  --what=classified   Remove only classifier outputs (data/clean/<book>/classified)
  --what=ingest       Remove only ingest outputs (*.txt, *_meta.json, *.jsonl)
  --what=all          Remove both ingest and classifier outputs
  --dry-run=true      Show what would be removed without deleting

Examples:
  bash scripts/clean_artifacts.sh mvs --what=classified
  bash scripts/clean_artifacts.sh mvs --what=all --dry-run=false
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" || $# -lt 1 ]]; then
  usage
  exit 0
fi

BOOK="$1"; shift || true
WHAT="classified"
DRY_RUN="true"

# Parse flags
for arg in "$@"; do
  case "$arg" in
    --what=*) WHAT="${arg#*=}" ;;
    --dry-run=*) DRY_RUN="${arg#*=}" ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

# Guard: book must be simple token
if [[ ! "$BOOK" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "Refusing to operate on invalid book id: '$BOOK'" >&2
  exit 2
fi

BASE="data/clean/$BOOK"
if [[ ! -d "$BASE" ]]; then
  echo "Directory not found: $BASE" >&2
  exit 1
fi

say() { echo -e "$*"; }

# Build delete lists
declare -a paths
if [[ "$WHAT" == "classified" || "$WHAT" == "all" ]]; then
  paths+=("$BASE/classified")
fi
if [[ "$WHAT" == "ingest" || "$WHAT" == "all" ]]; then
  # Common ingest outputs
  paths+=(
    "$BASE"/*_raw.txt
    "$BASE"/*_well_done.txt
    "$BASE"/*_ingest_meta.json
    "$BASE"/*_well_done.jsonl
    "$BASE"/*_well_done_meta.json
  )
fi

say "Cleaning artifacts in: $BASE"
say "Mode: $WHAT | Dry-run: $DRY_RUN"

# Expand globs safely
shopt -s nullglob

# Collect existing entries only
declare -a to_delete
for p in "${paths[@]}"; do
  for e in $p; do
    [[ -e "$e" ]] && to_delete+=("$e")
  done
done

if (( ${#to_delete[@]} == 0 )); then
  say "Nothing to delete."
  exit 0
fi

say "Items to delete ("${#to_delete[@]}" entries):"
for e in "${to_delete[@]}"; do
  echo "  - $e"
  if [[ "$DRY_RUN" == "false" ]]; then
    rm -rf -- "$e"
  fi
done

if [[ "$DRY_RUN" == "true" ]]; then
  say "Dry-run complete. Re-run with --dry-run=false to apply."
else
  say "Deletion complete."
fi
