#!/bin/bash
# Start the GSL FastAPI backend. Path-relative so it runs anywhere (not tied to
# Replit's /home/runner/workspace layout).
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
HOST="${GSL_HOST:-0.0.0.0}"
PORT="${GSL_BACKEND_PORT:-8000}"
exec python3 -m uvicorn main:app --host "$HOST" --port "$PORT"
