#!/bin/sh
set -e

echo "[entrypoint] Running alembic migrations..."
alembic upgrade head

if [ "${INGEST_ON_STARTUP}" = "true" ]; then
  echo "[entrypoint] INGEST_ON_STARTUP=true — running ingestion script"
  python backend/scripts/ingest_sebi_documents.py || echo "[entrypoint] ingestion failed but continuing"
fi

echo "[entrypoint] Starting Uvicorn..."
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
