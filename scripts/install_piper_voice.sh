#!/usr/bin/env bash
# Install a single Piper voice by id or relative path.
#
# Usage:
#   scripts/install_piper_voice.sh --id en_US-libritts-high [--dest DIR]
#   scripts/install_piper_voice.sh --rel en/en_US/libritts/high/en_US-libritts-high [--dest DIR]
#
# Default destination: ~/.local/share/piper/voices

set -euo pipefail

BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
DEST_DIR="${HOME}/.local/share/piper/voices"
ID=""
REL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --id)
      ID="$2"; shift 2 ;;
    --rel)
      REL="$2"; shift 2 ;;
    --dest)
      DEST_DIR="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,80p' "$0"; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "${ID}" && -z "${REL}" ]]; then
  echo "Error: provide --id or --rel" >&2
  exit 2
fi

need_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required tool '$1' not found in PATH" >&2
    exit 1
  fi
}

need_tool curl

# If only ID is given (e.g., en_US-libritts-high), derive REL path
if [[ -z "${REL}" ]]; then
  # ID format: <locale>-<name>-<quality>
  locale="${ID%%-*}"          # en_US
  rest="${ID#*-}"             # libritts-high
  name="${rest%-*}"           # libritts
  quality="${ID##*-}"         # high
  lang="${locale%%_*}"        # en
  REL="${lang}/${locale}/${name}/${quality}/${ID}"
fi

id_leaf="${REL##*/}"
out_dir="${DEST_DIR}/${id_leaf}"
model_url="${BASE_URL}/${REL}.onnx"
cfg_url="${BASE_URL}/${REL}.onnx.json"
model_path="${out_dir}/${id_leaf}.onnx"
cfg_path="${out_dir}/${id_leaf}.onnx.json"

echo "Installing ${id_leaf} -> ${out_dir}" >&2
mkdir -p "${out_dir}"

if [[ -f "${model_path}" ]]; then
  echo "- model exists, skipping" >&2
else
  echo "- downloading model" >&2
  curl -fL --retry 3 --retry-delay 2 -o "${model_path}" "${model_url}"
fi

if [[ -f "${cfg_path}" ]]; then
  echo "- config exists, skipping" >&2
else
  echo "- downloading config" >&2
  curl -fL --retry 3 --retry-delay 2 -o "${cfg_path}" "${cfg_url}"
fi

echo "Done. Verify with:\n  python -m abm.voice.piper_catalog --json" >&2
