"""
Pydantic schemas for ingestion endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ============================================================
# REQUEST MODELS
# ============================================================

class IngestRequest(BaseModel):
    """Request body for POST /ingest."""
    raw_text: str = Field(
        ...,
        min_length=1,
        description="Raw regulatory text to extract rules from",
        examples=[
            "Long term borrowings of State Governments raised from cooperative banks only are not eligible for agency commission."
        ],
    )
    source: str = Field(
        default="UNKNOWN",
        description="Regulatory source (e.g., RBI, SEBI)",
    )


class BatchIngestRequest(BaseModel):
    """Request body for POST /ingest/batch."""
    items: List[IngestRequest] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of raw texts to ingest",
    )


class ManualDocumentIngestRequest(BaseModel):
    """Request body for manual regulator-document ingestion."""
    file_path: str = Field(
        ...,
        min_length=1,
        description="Absolute or workspace-local path to a reviewed document file",
        examples=["documents/sebi/sample_circular.txt"],
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Human-readable document title",
    )
    source: str = Field(
        default="SEBI",
        description="Document source, typically SEBI for manual-assisted ingestion",
    )
    official_url: Optional[str] = Field(
        default=None,
        description="Official webpage or PDF URL when available",
    )
    published_date: Optional[str] = Field(
        default=None,
        description="Optional published date string for the source document",
    )


# ============================================================
# RESPONSE MODELS
# ============================================================

class IngestRuleResult(BaseModel):
    """Result for a single ingested rule."""
    status: str
    rule_id: Optional[str] = None
    rule_hash: Optional[str] = None
    version: Optional[int] = None
    detail: Optional[str] = None


class IngestResponse(BaseModel):
    """Response for POST /ingest."""
    status: str
    rules: List[IngestRuleResult]
    total_extracted: int
    total_stored: int
    total_skipped: int


class BatchIngestResponse(BaseModel):
    """Response for POST /ingest/batch."""
    status: str
    results: List[IngestResponse]
    total_texts: int


class ManualDocumentIngestResponse(BaseModel):
    status: str
    source: str
    title: str
    url: str
    file_path: Optional[str] = None
    rules: List[Dict[str, Any]]
    total_extracted: int
    detail: Optional[str] = None
