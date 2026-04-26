"""
Security helpers for optional endpoint protection.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException


INGEST_AUTH_ENABLED = os.getenv("INGEST_AUTH_ENABLED", "false").lower() == "true"
INGEST_API_KEY = os.getenv("INGEST_API_KEY", "").strip()


def require_ingestion_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not INGEST_AUTH_ENABLED:
        return

    if not INGEST_API_KEY:
        raise HTTPException(status_code=500, detail="INGEST_AUTH_ENABLED is true but INGEST_API_KEY is not configured.")

    if (x_api_key or "").strip() != INGEST_API_KEY:
        raise HTTPException(status_code=401, detail="Valid x-api-key header required for ingestion endpoints.")
