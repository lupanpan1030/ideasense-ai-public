#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY="${APPLY:-0}"

paths=(
  ".next"
  ".mypy_cache"
  ".pytest_cache"
  ".ruff_cache"
  "frontend/.next"
  "frontend/test-results"
  "frontend/tsconfig.tsbuildinfo"
)

prune_args=(
  -path "$ROOT_DIR/.git"
  -o -path "$ROOT_DIR/.agent"
  -o -path "$ROOT_DIR/.agents"
  -o -path "$ROOT_DIR/.claude"
  -o -path "$ROOT_DIR/.codex"
  -o -path "$ROOT_DIR/.cursor"
  -o -path "$ROOT_DIR/.kiro"
  -o -path "$ROOT_DIR/.shared"
  -o -path "$ROOT_DIR/.venv"
  -o -path "$ROOT_DIR/.venv-smoke"
  -o -path "$ROOT_DIR/.windsurf"
  -o -path "$ROOT_DIR/artifacts"
  -o -path "$ROOT_DIR/frontend/node_modules"
  -o -path "$ROOT_DIR/logs"
  -o -path "$ROOT_DIR/node_modules"
  -o -path "$ROOT_DIR/output"
)

list_artifacts() {
  local print_action="$1"

  find "$ROOT_DIR" \
    "(" "${prune_args[@]}" ")" -prune \
    -o -name "__pycache__" -type d "$print_action" -prune \
    -o "(" -name ".DS_Store" -o -name "*.pyc" ")" "$print_action"
}

echo "Known local artifact paths:"
for relative_path in "${paths[@]}"; do
  target="$ROOT_DIR/$relative_path"
  if [[ -e "$target" ]]; then
    echo "$target"
  fi
done

echo
echo "Discovered Python/macOS artifacts:"
list_artifacts -print

if [[ "$APPLY" != "1" ]]; then
  echo
  echo "Dry run only. Re-run with APPLY=1 to delete these local artifacts."
  exit 0
fi

for relative_path in "${paths[@]}"; do
  target="$ROOT_DIR/$relative_path"
  if [[ -e "$target" ]]; then
    rm -rf "$target"
  fi
done

list_artifacts -print0 | xargs -0 rm -rf

echo
echo "Local artifact cleanup complete."
