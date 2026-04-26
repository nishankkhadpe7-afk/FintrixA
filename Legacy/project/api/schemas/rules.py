"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ============================================================
# REQUEST MODELS
# ============================================================

class EvaluateRequest(BaseModel):
    """Request body for /evaluate and /debug endpoints."""
    data: Dict[str, Any] = Field(
        ...,
        description="Input data to evaluate against all active rules",
        min_length=1,
        examples=[{
            "borrower_type": "state_government",
            "loan_term": "long_term",
            "lender_type": "cooperative_bank"
        }]
    )


# ============================================================
# RESPONSE MODELS
# ============================================================

class MatchedRule(BaseModel):
    """A single matched rule."""
    rule_id: str
    version: int
    type: str
    action: str
    matched: bool = True


class EvaluateResponse(BaseModel):
    """Response for /evaluate endpoint."""
    matched_rules: List[str] = Field(
        description="List of matched rule IDs"
    )
    total_matches: int
    rules: List[MatchedRule]


class ConditionTrace(BaseModel):
    """Debug trace for a single condition evaluation."""
    type: str
    field: Optional[str] = None
    operator: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    result: Optional[bool] = None
    # For group nodes
    logic: Optional[str] = None
    children: Optional[List["ConditionTrace"]] = None
    results: Optional[List[bool]] = None
    final: Optional[bool] = None


class RuleTrace(BaseModel):
    """Debug trace for a single rule."""
    rule_id: str
    version: int
    type: str
    action: str
    result: bool
    trace: Dict[str, Any]


class DebugResponse(BaseModel):
    """Response for /debug endpoint."""
    input_data: Dict[str, Any]
    total_rules_evaluated: int
    matched_rules: List[str]
    total_matches: int
    rules: List[RuleTrace]
