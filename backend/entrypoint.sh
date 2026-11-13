#!/usr/bin/env sh
set -e

echo "[STARTUP] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[STARTUP] Starting Uvicorn on host 0.0.0.0, port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

