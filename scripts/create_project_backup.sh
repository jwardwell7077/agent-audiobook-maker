#!/usr/bin/env bash
set -euo pipefail

# create_project_backup.sh
# Creates a compressed tarball of the entire project (excluding common large/virtualenv dirs)
# and stores it one directory level above the repository root.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT_DIR="$(cd "$REPO_ROOT/.." && pwd)"
TS="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="agent-audiobook-maker-backup_${TS}.tar.gz"
ARCHIVE_PATH="$PARENT_DIR/$ARCHIVE_NAME"

echo "[backup] Repository root: $REPO_ROOT"
echo "[backup] Parent directory: $PARENT_DIR"
echo "[backup] Creating archive: $ARCHIVE_PATH"

# Build an exclusion list. Adjust as needed.
EXCLUDES=(
  --exclude '.git'
  --exclude '.venv*'
  --exclude 'venv'
  --exclude '__pycache__'
  --exclude '.pytest_cache'
  --exclude '.mypy_cache'
  --exclude '*.log'
  --exclude 'logs'
  --exclude '*.tar.gz'
  --exclude '*.tgz'
  --exclude 'agent-audiobook-maker-backup.mirror'
)

# shellcheck disable=SC2068
 tar -czf "$ARCHIVE_PATH" -C "$REPO_ROOT/.." "$(basename "$REPO_ROOT")" ${EXCLUDES[@]} 2> >(grep -v 'socket ignored' || true)

echo "[backup] Archive created: $ARCHIVE_PATH"
echo "[backup] Done."
