#!/usr/bin/env bash
set -euo pipefail

# Collect staged files
mapfile -d '' files < <(git diff --cached --name-only -z)

if (( ${#files[@]} == 0 )); then
  exit 0
fi

blocked=()

is_binary_ext() {
  local f="$1"
  shopt -s nocasematch
  case "$f" in
    *.wav|*.mp3|*.opus|*.m4a|*.m4b|*.aac|*.flac|*.ogg|*.aiff|*.aif|*.caf|
    *.mp4|*.webm|*.mkv|*.mov|*.avi|
    *.zip|*.tar|*.tgz|*.tar.gz|*.7z|
    *.pdf|*.bin|*.dat|*.db|*.sqlite|*.pkl|*.pickle|
    *.jpg|*.jpeg|*.png|*.gif|*.webp|*.svg)
      return 0 ;;
    *) return 1 ;;
  esac
}

for f in "${files[@]}"; do
  # Always allow under docs/
  if [[ "$f" == docs/* ]]; then
    continue
  fi

  # Allow under tests/ (test names may contain keywords like 'mvs')
  if [[ "$f" == tests/* ]]; then
    continue
  fi

  # Block any path containing 'mvs' (case-insensitive)
  if [[ "$f" =~ [Mm][Vv][Ss] ]]; then
    blocked+=("$f [contains 'mvs']")
    continue
  fi

  # Block data/ except SAMPLE_BOOK subtrees
  if [[ "$f" == data/* ]]; then
    if [[ "$f" != data/books/SAMPLE_BOOK/* &&
          "$f" != data/clean/SAMPLE_BOOK/* &&
          "$f" != data/annotations/SAMPLE_BOOK/* &&
          "$f" != data/renders/SAMPLE_BOOK/* &&
          "$f" != data/stems/SAMPLE_BOOK/* &&
          "$f" != data/clean/SAMPLE_BOOK &&
          "$f" != data/annotations/SAMPLE_BOOK &&
          "$f" != data/renders/SAMPLE_BOOK &&
          "$f" != data/stems/SAMPLE_BOOK ]]; then
      blocked+=("$f [data/ not in SAMPLE_BOOK]")
      continue
    fi
  fi

  # Block logs and temp
  if [[ "$f" == run_logs/* || "$f" == stageB/run_logs/* || "$f" == tmp/* || "$f" == temp/* ]]; then
    blocked+=("$f [logs/temp]")
    continue
  fi

  # Block binary/media extensions outside docs/
  if is_binary_ext "$f"; then
    blocked+=("$f [binary/media]")
    continue
  fi

  # Block known book metadata
  if [[ "$f" == data/book.yaml || "$f" == data/cover.jpg || "$f" == data/cover.png ]]; then
    blocked+=("$f [book metadata]")
    continue
  fi

done

if (( ${#blocked[@]} > 0 )); then
  echo "\nERROR: Commit blocked by prevent_private_data hook. The following paths are not allowed:" >&2
  for b in "${blocked[@]}"; do
    echo "  - $b" >&2
  done
  echo "\nIf this is intentional, place files in docs/ (for diagrams/images) or sample-only paths under data/**/SAMPLE_BOOK/**.\n" >&2
  echo "To bypass in an emergency (not recommended): git commit --no-verify" >&2
  exit 1
fi

exit 0
