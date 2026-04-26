"""
SQLAlchemy models for the integrated Fintrix Rule Engine.
Stores compliance rules in S92's existing SQLite database.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float
from datetime import datetime, timezone
from backend.database import Base


class ComplianceRule(Base):
    """
    A structured compliance rule extracted from regulatory documents.
    Ported from Fintrix's PostgreSQL schema to SQLite.
    """
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String, unique=False, index=True)
    version = Column(Integer, default=1)
    domain = Column(String, index=True)        # lending, forex, trading, bonds
    type = Column(String)                       # threshold, eligibility, reporting, restriction
    title = Column(String, nullable=False)
    description = Column(Text)
    canonical_rule = Column(Text, nullable=False)  # JSON: {logic, conditions}
    action = Column(String)                     # flag, block, allow, review
    source_document = Column(String)
    source_page = Column(Integer)
    source_url = Column(String)
    regulator = Column(String)                  # RBI, SEBI, IT
    severity = Column(String, default="medium") # low, medium, high, critical
    is_active = Column(Boolean, default=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class RuleEvaluation(Base):
    """
    Logs each rule evaluation for audit trail / traceability.
    """
    __tablename__ = "rule_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    rule_id = Column(String)
    input_summary = Column(Text)
    matched = Column(Boolean)
    trace = Column(Text)  # JSON debug trace
    source = Column(String)  # "ai_agent", "whatif", "manual"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
