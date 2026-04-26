from pydantic import BaseModel, validator, ConfigDict
from typing import List, Union, Optional, Any

ALLOWED_OPERATORS = {">", "<", ">=", "<=", "==", "!=", "contains", "exists", "not_in"}
ALLOWED_LOGICS = {"AND", "OR"}

class Condition(BaseModel):
    field: str
    operator: str
    value: Union[int, float, str, list]

    @validator("operator")
    def validate_operator(cls, v):
        if v not in ALLOWED_OPERATORS:
            raise ValueError(f"Invalid operator: {v}")
        return v


class Rule(BaseModel):
    model_config = ConfigDict(extra="allow")  # Allow flexible structure
    
    type: str
    action: str
    logic: Optional[str] = "AND"
    conditions: List[Any] = []

    @validator("type")
    def validate_type(cls, v):
        allowed = {"eligibility", "prohibition", "conditional", "aggregation", "restriction", "obligation", "exception"}
        if v not in allowed:
            raise ValueError(f"Invalid type: {v}")
        return v
    
    @validator("logic")
    def validate_logic(cls, v):
        if v and v not in ALLOWED_LOGICS:
            raise ValueError(f"Invalid logic: {v}")
        return v or "AND"
