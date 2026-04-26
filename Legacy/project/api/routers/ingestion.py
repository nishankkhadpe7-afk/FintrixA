"""
Router: rule ingestion endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.ingest import (
    IngestRequest,
    IngestResponse,
    BatchIngestRequest,
    BatchIngestResponse,
    ManualDocumentIngestRequest,
    ManualDocumentIngestResponse,
)
from api.services import ingestion_service
from api.core.exceptions import EngineError
from api.security import require_ingestion_api_key

router = APIRouter(prefix="/ingest", tags=["Ingestion"], dependencies=[Depends(require_ingestion_api_key)])


@router.post("", response_model=IngestResponse)
def ingest_rule(request: IngestRequest):
    """
    Ingest raw regulatory text → extract, normalize, validate, store.
    """
    try:
        result = ingestion_service.ingest_rule(request.raw_text, request.source)
        return result

    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)


@router.post("/batch", response_model=BatchIngestResponse)
def ingest_batch(request: BatchIngestRequest):
    """
    Ingest multiple raw texts in a single request.
    Each text is processed independently.
    """
    results = []

    for item in request.items:
        try:
            result = ingestion_service.ingest_rule(item.raw_text, item.source)
            results.append(result)
        except EngineError as e:
            results.append({
                "status": "error",
                "rules": [],
                "total_extracted": 0,
                "total_stored": 0,
                "total_skipped": 0,
            })

    return {
        "status": "success",
        "results": results,
        "total_texts": len(request.items),
    }


@router.post("/manual-document", response_model=ManualDocumentIngestResponse)
def ingest_manual_document(request: ManualDocumentIngestRequest):
    """
    Ingest a reviewed local regulator document, such as an official SEBI PDF or text export.
    """
    try:
        return ingestion_service.ingest_manual_document(
            file_path=request.file_path,
            title=request.title,
            source=request.source,
            official_url=request.official_url,
            published_date=request.published_date,
        )
    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)
