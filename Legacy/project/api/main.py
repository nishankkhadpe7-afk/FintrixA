"""
FastAPI Application — Rule Engine API
"""

import logging
import os
import time
from collections import defaultdict, deque
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from api.routers import rules, ingestion, simulation, rbi_ingestion, circulars, sebi_ingestion
from api.core.exceptions import EngineError, InvalidInputError
from api.services import ingestion_service

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

API_AUTH_ENABLED = os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
API_KEY = os.getenv("API_KEY", "").strip()
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
SIM_RATE_LIMIT = int(os.getenv("SIM_RATE_LIMIT", "30"))
INGEST_RATE_LIMIT = int(os.getenv("INGEST_RATE_LIMIT", "5"))
AUTH_EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/docs/oauth2-redirect",
}
RATE_LIMIT_BUCKETS = defaultdict(deque)

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="RegTech Rule Engine API",
    description="Deterministic regulatory rule evaluation engine with debug tracing",
    version="1.0.0",
)

# CORS — allow React frontend
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def optional_api_key_auth(request: Request, call_next):
    if not API_AUTH_ENABLED:
        return await call_next(request)

    path = request.url.path
    if path in AUTH_EXEMPT_PATHS or path.startswith("/docs"):
        return await call_next(request)

    if not API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "server_misconfigured", "detail": "API auth is enabled but API_KEY is not configured."},
        )

    provided = request.headers.get("x-api-key", "").strip()
    if provided != API_KEY:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "detail": "Valid x-api-key header required."},
        )

    return await call_next(request)


@app.middleware("http")
async def basic_rate_limit(request: Request, call_next):
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    path = request.url.path
    if path in AUTH_EXEMPT_PATHS or path.startswith("/docs"):
        return await call_next(request)

    limit = None
    if path in {"/simulate", "/rules/simulate"}:
        limit = SIM_RATE_LIMIT
    elif path.startswith("/ingest") or path.startswith("/rbi/ingest") or path.startswith("/sebi/discover"):
        limit = INGEST_RATE_LIMIT

    if limit is None:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    bucket_key = f"{client_ip}:{path}"
    bucket = RATE_LIMIT_BUCKETS[bucket_key]
    now = time.time()

    while bucket and bucket[0] <= now - RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= limit:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "detail": f"Too many requests for {path}. Please retry later."},
        )

    bucket.append(now)
    return await call_next(request)


# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(InvalidInputError)
async def invalid_input_handler(request: Request, exc: InvalidInputError):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_input", "detail": exc.detail},
    )


@app.exception_handler(EngineError)
async def engine_error_handler(request: Request, exc: EngineError):
    return JSONResponse(
        status_code=500,
        content={"error": "engine_error", "detail": exc.detail},
    )


# ============================================================
# ROUTERS
# ============================================================

app.include_router(rules.router)
app.include_router(ingestion.router)
app.include_router(simulation.router, prefix="/rules")
app.include_router(rbi_ingestion.router)
app.include_router(sebi_ingestion.router)
app.include_router(circulars.router)


@app.get("/", tags=["System"])
def root():
    return {
        "name": "RegTech Rule Engine API",
        "status": "ok",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "stats": "/stats",
        "simulate": "/simulate",
    }

# Direct simulate endpoint for easier access (mirrors /rules/simulate)
from api.schemas.simulate import SimulationRequest, SimulationResponse
from api.services import simulation_service

@app.post("/simulate", response_model=SimulationResponse, tags=["Simulation"])
async def direct_simulate(
    request: SimulationRequest,
    debug: bool = False,
):
    """
    Direct simulate endpoint (also available at /rules/simulate).
    Evaluate multiple input scenarios against all active rules.
    """
    try:
        result = simulation_service.simulate(request.inputs, debug=debug)
        logging.getLogger(__name__).info(f"Simulation completed: {result.get('total_matches', 0)} matches")
        return result
    except EngineError as e:
        logging.getLogger(__name__).error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=e.detail)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}


@app.get("/stats", tags=["System"])
def dashboard_stats():
    return ingestion_service.get_dashboard_stats()
