"""
Router: circular retrieval endpoints for the frontend.
"""

from fastapi import APIRouter, HTTPException

from api.services import ingestion_service
from api.core.exceptions import EngineError

router = APIRouter(tags=["Circulars"])


@router.get("/circulars")
def list_circulars():
    """
    Return ingested circulars.
    """
    try:
        return ingestion_service.list_circulars()
    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)


@router.get("/circulars/{circular_id}")
def get_circular(circular_id: str):
    """
    Return a single circular by id.
    """
    try:
        return ingestion_service.get_circular(circular_id)
    except EngineError as e:
        status_code = 404 if "not found" in e.detail.lower() else 500
        raise HTTPException(status_code=status_code, detail=e.detail)
