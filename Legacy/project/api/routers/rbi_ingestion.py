"""
Router: RBI circular ingestion trigger endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ingestion.pipeline_orchestrator import run_pipeline
from api.core.exceptions import EngineError
from api.security import require_ingestion_api_key

router = APIRouter(tags=["RBI Ingestion"], dependencies=[Depends(require_ingestion_api_key)])


@router.post("/rbi/ingest")
def trigger_rbi_ingestion(
    max_entries: int = Query(10, ge=1, le=50, description="Max circulars to process"),
):
    """
    Trigger RBI circular ingestion pipeline.

    Fetches RSS feed, scrapes new circulars, extracts rules via LLM,
    and returns structured output ready for downstream pipeline.
    """
    try:
        results = run_pipeline(max_entries=max_entries)

        total_rules = sum(len(r.get("rules", [])) for r in results)

        return {
            "status": "success",
            "circulars_processed": len(results),
            "total_rules_extracted": total_rules,
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion pipeline failed: {str(e)}")
