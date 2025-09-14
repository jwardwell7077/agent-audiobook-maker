#!/usr/bin/env bash
# Install all (or a filtered set of) Piper voices to a local directory.
#
# This script scrapes the official VOICES.md from the Piper repo to get the
# list of voice model/config URLs, then downloads them locally.
#
# CAUTION: Downloading ALL voices can be many gigabytes. Use filters.
#
# Usage:
#   scripts/install_piper_voices_all.sh [--dest DIR] [--lang LANG] [--quality Q]
#                                       [--jobs N] [--yes] [--list-only]
#
# Examples:
#   # Install all English voices
#   scripts/install_piper_voices_all.sh --lang en
#
#   # Install only high/medium quality US English voices
#   scripts/install_piper_voices_all.sh --lang en_US --quality "high|medium"
#
#   # Just list what would be downloaded
#   scripts/install_piper_voices_all.sh --lang en --list-only

set -euo pipefail

VOICES_MD_URL="https://raw.githubusercontent.com/rhasspy/piper/master/VOICES.md"
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
DEST_DIR="${HOME}/.local/share/piper/voices"
LANG_FILTER=""
QUALITY_FILTER=""
JOBS="4"
ASSUME_YES="0"
LIST_ONLY="0"
DEDUPE_BY_NAME="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      DEST_DIR="$2"; shift 2 ;;
    --lang)
      LANG_FILTER="$2"; shift 2 ;;
    --quality)
      QUALITY_FILTER="$2"; shift 2 ;;
    --jobs|-j)
      JOBS="$2"; shift 2 ;;
    --yes|-y)
      ASSUME_YES="1"; shift 1 ;;
    --list-only)
      LIST_ONLY="1"; shift 1 ;;
    --dedupe-by-name)
      DEDUPE_BY_NAME="1"; shift 1 ;;
    -h|--help)
      sed -n '1,80p' "$0"; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

need_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required tool '$1' not found in PATH" >&2
    exit 1
  fi
}

need_tool curl
need_tool awk
need_tool grep
need_tool sed
need_tool xargs

mkdir -p "${DEST_DIR}"

echo "Fetching voice catalog..." >&2
VOICES_MD_CONTENT=$(curl -fsSL "${VOICES_MD_URL}")

# Extract relative model paths from VOICES.md
# Pattern: ... resolve/v1.0.0/<rel-path>.onnx
REL_PATHS=$(printf "%s\n" "${VOICES_MD_CONTENT}" \
  | grep -Eo 'resolve/v1\.0\.0/[^"\)\?]+\.onnx(\?download=true)?' \
  | sed -E 's#^resolve/v1.0.0/##; s/\?download=true$//' \
  | sort -u)

# Apply language filter if provided (matches at the beginning of path or anywhere)
if [[ -n "${LANG_FILTER}" ]]; then
  REL_PATHS=$(printf "%s\n" "${REL_PATHS}" | grep -E "/${LANG_FILTER}/|^${LANG_FILTER}/" || true)
fi

# Apply quality filter if provided (regex of qualities: low|medium|high|x_low)
if [[ -n "${QUALITY_FILTER}" ]]; then
  REL_PATHS=$(printf "%s\n" "${REL_PATHS}" | grep -E "/(${QUALITY_FILTER})/" || true)
fi

# Build a list of base ids and URLs (without extension)
# Example rel: en/en_US/ryan/high/en_US-ryan-high
BASE_IDS=$(printf "%s\n" "${REL_PATHS}" | sed -E 's/\.onnx$//' | sort -u)

# Optionally de-duplicate by base name (strip locale and quality from id)
if [[ "${DEDUPE_BY_NAME}" == "1" ]]; then
  declare -A BEST_REL=()
  declare -A BEST_LOC=()
  while IFS= read -r rel_noext; do
    [[ -z "${rel_noext}" ]] && continue
    id="${rel_noext##*/}"             # en_US-ryan-high
    loc=$(printf "%s" "${rel_noext}" | awk -F'/' '{print $2}') # en_US or en_GB
    name=$(printf "%s" "${id}" | sed -E 's/^[^-]+-//; s/-[^-]+$//')
    if [[ -z "${BEST_REL[${name}]:-}" ]]; then
      BEST_REL["${name}"]="${rel_noext}"
      BEST_LOC["${name}"]="${loc}"
    else
      # Prefer en_US over other locales when names collide
      prev_loc="${BEST_LOC[${name}]}"
      if [[ "${prev_loc}" != "en_US" && "${loc}" == "en_US" ]]; then
        BEST_REL["${name}"]="${rel_noext}"
        BEST_LOC["${name}"]="${loc}"
      fi
    fi
  done < <(printf "%s\n" "${BASE_IDS}")

  # Rebuild BASE_IDS from map values, sorted for determinism
  BASE_IDS=$(for k in "${!BEST_REL[@]}"; do printf "%s\n" "${BEST_REL[$k]}"; done | sort -u)
fi

COUNT=$(printf "%s\n" "${BASE_IDS}" | grep -c . || true)
if [[ -z "${COUNT}" ]]; then COUNT=0; fi

echo "Voices matched: ${COUNT}" >&2

if [[ "${LIST_ONLY}" == "1" ]]; then
  printf "%s\n" "${BASE_IDS}"
  exit 0
fi

if [[ "${COUNT}" -gt 50 && "${ASSUME_YES}" != "1" ]]; then
  echo "WARNING: This will download a large number of voices (>${COUNT})." >&2
  echo "Destination: ${DEST_DIR}" >&2
  read -r -p "Proceed? [y/N] " ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

echo "Downloading to: ${DEST_DIR}" >&2

download_one() {
  local rel_noext="$1"   # en/en_US/ryan/high/en_US-ryan-high
  local id; id="${rel_noext##*/}"
  local out_dir="${DEST_DIR}/${id}"
  local model_url="${BASE_URL}/${rel_noext}.onnx"
  local cfg_url="${BASE_URL}/${rel_noext}.onnx.json"
  local model_path="${out_dir}/${id}.onnx"
  local cfg_path="${out_dir}/${id}.onnx.json"

  mkdir -p "${out_dir}"

  if [[ -f "${model_path}" ]]; then
    echo "- ${id}: model exists, skipping" >&2
  else
    echo "- ${id}: downloading model" >&2
    if ! curl -fL --retry 3 --retry-delay 2 -o "${model_path}" "${model_url}"; then
      echo "  ! failed model: ${model_url}" >&2
      rm -f "${model_path}" || true
      return 1
    fi
  fi

  if [[ -f "${cfg_path}" ]]; then
    echo "- ${id}: config exists, skipping" >&2
  else
    echo "- ${id}: downloading config" >&2
    if ! curl -fL --retry 3 --retry-delay 2 -o "${cfg_path}" "${cfg_url}"; then
      echo "  ! failed config: ${cfg_url}" >&2
      rm -f "${cfg_path}" || true
      return 1
    fi
  fi
}

# Export for xargs -P
export -f download_one
export DEST_DIR BASE_URL

printf "%s\n" "${BASE_IDS}" | xargs -I {} -P "${JOBS}" bash -c 'download_one "$@"' _ {}

echo "Done. Verify with:"
echo "  python -m abm.voice.piper_catalog --json"
