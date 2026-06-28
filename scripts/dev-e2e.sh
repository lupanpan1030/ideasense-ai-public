#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8003}"
FRONTEND_PORT="${FRONTEND_PORT:-3002}"
BACKEND_ORIGIN="http://localhost:${FRONTEND_PORT}"
API_BASE_URL="http://localhost:${BACKEND_PORT}/api/v1"

if [[ -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]]; then
  BACKEND_CMD=("$ROOT_DIR/backend/.venv/bin/uvicorn" "app.main:app" "--reload" "--port" "$BACKEND_PORT" "--app-dir" "$ROOT_DIR/backend")
elif command -v uvicorn >/dev/null 2>&1; then
  BACKEND_CMD=("uvicorn" "app.main:app" "--reload" "--port" "$BACKEND_PORT" "--app-dir" "$ROOT_DIR/backend")
else
  echo "uvicorn not found. Activate backend/.venv or install backend dependencies." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js first." >&2
  exit 1
fi

echo "Starting E2E backend on http://127.0.0.1:${BACKEND_PORT}"
echo "Email verification links will be printed in backend logs."
(
  cd "$ROOT_DIR/backend"
  APP_ENV="${APP_ENV:-development}" \
  RESEND_API_KEY= \
  EMAIL_LOG_TOKEN_LINKS=1 \
  EMAIL_VERIFY_BASE_URL="$BACKEND_ORIGIN" \
  CORS_ALLOW_ORIGINS="$BACKEND_ORIGIN,http://127.0.0.1:${FRONTEND_PORT}" \
  "${BACKEND_CMD[@]}"
) &
BACKEND_PID=$!

echo "Starting E2E frontend on http://localhost:${FRONTEND_PORT}"
NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" \
  npm --prefix "$ROOT_DIR/frontend" run dev -- --hostname localhost --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

cleanup() {
  echo "Shutting down E2E dev servers..."
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
