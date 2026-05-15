#!/usr/bin/env bash
set -euo pipefail

APP_PYTHON="${APP_PYTHON:-/home/cguiesc/venvs/app/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8001}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
OLLAMA_BIN="${OLLAMA_BIN:-$(command -v ollama || true)}"
export CROPEAR_PADDLE_DEVICE="${CROPEAR_PADDLE_DEVICE:-cpu}"
export OLLAMA_BASE_URL

ollama_ready() {
  "$APP_PYTHON" - "$OLLAMA_BASE_URL" <<'PY'
import sys
import requests

base_url = sys.argv[1].rstrip("/")
try:
    response = requests.get(f"{base_url}/api/tags", timeout=2)
    response.raise_for_status()
except Exception:
    raise SystemExit(1)
PY
}

if ! ollama_ready; then
  if [[ -z "$OLLAMA_BIN" ]]; then
    echo "Ollama is not reachable at ${OLLAMA_BASE_URL} and no ollama binary was found." >&2
    echo "Start Ollama manually, then rerun this script." >&2
    exit 1
  fi

  echo "Ollama is not reachable at ${OLLAMA_BASE_URL}; starting Ollama..."
  nohup env OLLAMA_HOST="$OLLAMA_HOST" "$OLLAMA_BIN" serve >/tmp/mathvision_ollama.log 2>&1 &

  for _ in {1..30}; do
    if ollama_ready; then
      break
    fi
    sleep 1
  done

  if ! ollama_ready; then
    echo "Ollama did not become ready at ${OLLAMA_BASE_URL}." >&2
    echo "See /tmp/mathvision_ollama.log for details." >&2
    exit 1
  fi
fi

while ss -ltn | awk '{print $4}' | grep -Eq "(:|\\])${PORT}$"; do
  PORT=$((PORT + 1))
done

echo "Using Ollama at ${OLLAMA_BASE_URL}"
echo "Starting MathVision AI on http://${HOST}:${PORT}"
exec "$APP_PYTHON" -m uvicorn backend.main:app --host "$HOST" --port "$PORT"
