"""
Router: SEBI RSS discovery endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ingestion.sebi_pipeline_orchestrator import run_sebi_discovery
from api.security import require_ingestion_api_key

router = APIRouter(tags=["SEBI Ingestion"], dependencies=[Depends(require_ingestion_api_key)])


@router.post("/sebi/discover")
def trigger_sebi_discovery(
    max_entries: int = Query(25, ge=1, le=100, description="Max SEBI RSS items to sync"),
):
    try:
        return run_sebi_discovery(max_entries=max_entries)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SEBI discovery failed: {exc}")
