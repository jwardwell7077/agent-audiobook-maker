#!/usr/bin/env bash
set -euo pipefail

HOOKS_DIR=".git/hooks"
mkdir -p "$HOOKS_DIR"
cat > "$HOOKS_DIR/pre-push" <<'EOF'
#!/usr/bin/env bash
set -e
if [ -f scripts/pre_push.sh ]; then
  bash scripts/pre_push.sh
fi
EOF
chmod +x "$HOOKS_DIR/pre-push"
echo "Installed pre-push hook."
