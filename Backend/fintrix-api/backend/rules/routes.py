"""
API Routes for the integrated Fintrix Rule Engine.
Provides endpoints for rule listing, evaluation, stats, and admin.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.auth.utils import decode_token
from backend.auth.models import User
from backend.rules.models import ComplianceRule, RuleEvaluation
from backend.rules.engine import (
    evaluate_all_rules,
    evaluate_for_scenario,
    get_rule_stats,
    get_trace_history,
    simulate_rules,
)
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user if authenticated, else None."""
    if not credentials:
        return None
    try:
        user_id = decode_token(credentials.credentials)
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


# ============================================================
# LIST RULES
# ============================================================

@router.get("/list")
def list_rules(
    domain: Optional[str] = Query(None, description="Filter by domain: forex, lending, trading, bonds, general"),
    regulator: Optional[str] = Query(None, description="Filter by regulator: RBI, SEBI, IT, FIU"),
    db: Session = Depends(get_db)
):
    """List all active compliance rules with optional filters."""
    query = db.query(ComplianceRule).filter(ComplianceRule.is_active == True)

    if domain:
        query = query.filter(ComplianceRule.domain == domain.lower())
    if regulator:
        query = query.filter(ComplianceRule.regulator == regulator.upper())

    rules = query.order_by(ComplianceRule.domain, ComplianceRule.rule_id).all()

    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "version": r.version,
            "domain": r.domain,
            "type": r.type,
            "title": r.title,
            "description": r.description,
            "action": r.action,
            "severity": r.severity,
            "regulator": r.regulator,
            "source_document": r.source_document,
            "source_url": r.source_url,
            "canonical_rule": json.loads(r.canonical_rule) if r.canonical_rule else None
        }
        for r in rules
    ]


# ============================================================
# EVALUATE RULES
# ============================================================

class EvaluateRequest(BaseModel):
    input_data: Dict[str, Any]
    domain: Optional[str] = None
    debug: bool = False


class SimulationRequest(BaseModel):
    inputs: List[Dict[str, Any]]
    domain: Optional[str] = None
    debug: bool = False


@router.post("/evaluate")
def evaluate_rules(
    data: EvaluateRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Evaluate all active rules against input data."""
    return evaluate_all_rules(
        db=db,
        input_data=data.input_data,
        domain=data.domain,
        debug=data.debug,
        source="manual",
        user_id=user.id if user else None
    )


@router.post("/simulate")
def simulate_rule_inputs(
    data: SimulationRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Evaluate multiple structured scenarios for the simulator UI."""
    if not data.inputs:
        raise HTTPException(status_code=400, detail="At least one input is required")

    return simulate_rules(
        db=db,
        inputs=data.inputs,
        domain=data.domain,
        debug=data.debug,
        source="simulation",
        user_id=user.id if user else None,
    )


# ============================================================
# SCENARIO EVALUATION (used by AI Agent & What-If)
# ============================================================

class ScenarioRequest(BaseModel):
    question: str
    event_types: List[str] = Field(default_factory=list)
    amount: int = 0


@router.post("/evaluate/scenario")
def evaluate_scenario(
    data: ScenarioRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Evaluate rules for a financial scenario (used by AI Agent and What-If)."""
    return evaluate_for_scenario(
        db=db,
        question=data.question,
        event_types=data.event_types,
        amount=data.amount,
        user_id=user.id if user else None,
        debug=False,
    )


# ============================================================
# RULE DETAILS
# ============================================================

@router.get("/detail/{rule_id}")
def get_rule_detail(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """Get full details of a specific rule."""
    rule = db.query(ComplianceRule).filter(
        ComplianceRule.rule_id == rule_id,
        ComplianceRule.is_active == True
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "id": rule.id,
        "rule_id": rule.rule_id,
        "version": rule.version,
        "domain": rule.domain,
        "type": rule.type,
        "title": rule.title,
        "description": rule.description,
        "action": rule.action,
        "severity": rule.severity,
        "regulator": rule.regulator,
        "source_document": rule.source_document,
        "source_url": rule.source_url,
        "canonical_rule": json.loads(rule.canonical_rule) if rule.canonical_rule else None,
        "confidence": rule.confidence,
        "created_at": str(rule.created_at),
        "updated_at": str(rule.updated_at)
    }


# ============================================================
# STATISTICS
# ============================================================

@router.get("/stats")
def rules_stats(db: Session = Depends(get_db)):
    """Get aggregate rule statistics for the dashboard."""
    return get_rule_stats(db)


@router.get("/trace")
def trace_history(
    rule_id: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Return recent evaluation traces with optional rule filtering."""
    items = get_trace_history(db, rule_id=rule_id, limit=limit)
    return {
        "count": len(items),
        "rule_id": rule_id,
        "items": items,
    }


# ============================================================
# EVALUATION HISTORY (audit trail)
# ============================================================

@router.get("/evaluations")
def list_evaluations(
    limit: int = Query(50, le=200),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List recent rule evaluations for audit trail."""
    query = db.query(RuleEvaluation)
    if source:
        query = query.filter(RuleEvaluation.source == source)
    evaluations = query.order_by(RuleEvaluation.created_at.desc()).limit(limit).all()
    return {
        "count": len(evaluations),
        "items": [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "matched": e.matched,
                "source": e.source,
                "input_summary": e.input_summary,
                "created_at": str(e.created_at),
            }
            for e in evaluations
        ],
    }
