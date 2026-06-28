#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]]; then
  BACKEND_CMD=("$ROOT_DIR/backend/.venv/bin/uvicorn" "app.main:app" "--reload" "--port" "8000" "--app-dir" "$ROOT_DIR/backend")
elif command -v uvicorn >/dev/null 2>&1; then
  BACKEND_CMD=("uvicorn" "app.main:app" "--reload" "--port" "8000" "--app-dir" "$ROOT_DIR/backend")
else
  echo "uvicorn not found. Activate backend/.venv or install backend dependencies." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js first." >&2
  exit 1
fi

echo "Starting backend on http://127.0.0.1:8000"
"${BACKEND_CMD[@]}" &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:3000"
npm --prefix "$ROOT_DIR/frontend" run dev &
FRONTEND_PID=$!

cleanup() {
  echo "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend exited; stopping frontend."
    break
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "Frontend exited; stopping backend."
    break
  fi
  sleep 1
done
