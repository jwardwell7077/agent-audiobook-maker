#!/usr/bin/env bash
# Install a small set of English Piper voices locally.
#
# Usage:
#   scripts/install_piper_voices.sh [DEST_DIR]
#
# If DEST_DIR is not provided, defaults to ~/.local/share/piper/voices
# The script will create a folder per voice id and download both the .onnx model
# and the matching .onnx.json config file.

set -euo pipefail

BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
DEST_DIR="${1:-$HOME/.local/share/piper/voices}"

echo "Installing Piper voices to: ${DEST_DIR}"
mkdir -p "${DEST_DIR}"

need_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required tool '$1' not found in PATH" >&2
    exit 1
  fi
}

need_tool curl

# Curated small set of English voices (good coverage for auditioning)
VOICES=(
  "en/en_US/ryan/high/en_US-ryan-high"
  "en/en_US/amy/medium/en_US-amy-medium"
  "en/en_GB/cori/medium/en_GB-cori-medium"
)

download_voice() {
  local rel="$1"        # e.g., en/en_US/ryan/high/en_US-ryan-high
  local id
  id="${rel##*/}"       # e.g., en_US-ryan-high
  local out_dir="${DEST_DIR}/${id}"
  local model_url="${BASE_URL}/${rel}.onnx"
  local cfg_url="${BASE_URL}/${rel}.onnx.json"
  local model_path="${out_dir}/${id}.onnx"
  local cfg_path="${out_dir}/${id}.onnx.json"

  mkdir -p "${out_dir}"

  if [[ -f "${model_path}" ]]; then
    echo "- Skipping ${id} model (already exists)"
  else
    echo "- Downloading ${id} model"
    curl -fL "${model_url}" -o "${model_path}"
  fi

  if [[ -f "${cfg_path}" ]]; then
    echo "- Skipping ${id} config (already exists)"
  else
    echo "- Downloading ${id} config"
    curl -fL "${cfg_url}" -o "${cfg_path}"
  fi
}

for v in "${VOICES[@]}"; do
  download_voice "${v}"
done

echo "\nDone. To verify discovery, run:"
echo "  python -m abm.voice.piper_catalog --json"
