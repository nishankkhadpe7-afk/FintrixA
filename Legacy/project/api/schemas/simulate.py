"""
Pydantic schemas for simulation endpoint.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ============================================================
# REQUEST
# ============================================================

class SimulationRequest(BaseModel):
    """Request body for POST /rules/simulate."""
    inputs: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of input scenarios to evaluate against all active rules",
        examples=[[
            {"borrower_type": "state_government", "lender_type": "cooperative_bank", "loan_term": "long_term"},
            {"borrower_type": "private_sector", "lender_type": "bank", "loan_term": "short_term"},
        ]],
    )


# ============================================================
# RESPONSE
# ============================================================

class MatchedRuleSummary(BaseModel):
    rule_id: str
    version: int
    type: str
    action: str
    title: str
    description: str


class SimulationResultItem(BaseModel):
    input: Dict[str, Any]
    matched_rules: List[MatchedRuleSummary]
    match_count: int
    trace: Optional[List[Dict[str, Any]]] = None


class SimulationResponse(BaseModel):
    request_id: str
    total_inputs: int
    total_matches: int
    results: List[SimulationResultItem]
