"""
Router: rule evaluation endpoints.
"""

from fastapi import APIRouter, HTTPException

from api.schemas.rules import (
    EvaluateRequest,
    EvaluateResponse,
    DebugResponse,
)
from api.services import rule_service
from api.core.exceptions import EngineError, InvalidInputError

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.get("")
def list_all_rules():
    """
    Return the latest version of each active rule.
    """
    try:
        return rule_service.list_rules()
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=e.detail)
    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)


@router.get("/{rule_id}")
def get_rule(rule_id: str):
    """
    Return a single active rule by rule_id.
    """
    try:
        return rule_service.get_rule(rule_id)
    except InvalidInputError as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_rules(request: EvaluateRequest):
    """
    Evaluate input data against all active rules.
    Returns matched rule IDs and actions.
    """
    try:
        result = rule_service.evaluate(request.data)
        return result

    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=e.detail)
    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)


@router.post("/debug", response_model=DebugResponse)
def debug_rules(request: EvaluateRequest):
    """
    Evaluate input data with full debug trace.
    Returns condition-level evaluation details for every rule.
    """
    try:
        result = rule_service.evaluate_debug(request.data)
        return result

    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=e.detail)
    except EngineError as e:
        raise HTTPException(status_code=500, detail=e.detail)
