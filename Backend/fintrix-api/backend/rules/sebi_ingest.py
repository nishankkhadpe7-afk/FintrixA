"""Reviewed SEBI document ingestion for the active FinTrix backend.

This module reuses the local, reviewed SEBI document corpus (manifest + PDFs)
and converts those documents into ComplianceRule rows using the existing
rule table. It is designed for official-source documents only.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field, ValidationError, conlist
from sqlalchemy.exc import SQLAlchemyError

from backend.database import SessionLocal
from backend.mistral_client import get_mistral_client
from backend.rules.models import ComplianceRule

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = PROJECT_ROOT / "Legacy" / "project" / "documents" / "sebi" / "manifest.json"
DEFAULT_DOC_ROOT = PROJECT_ROOT / "Legacy" / "project"


class IngestedCondition(BaseModel):
    field: str
    operator: str
    value: Any


class IngestedAction(BaseModel):
    result: str = Field(pattern="^(allow|deny|flag|require)$")
    message: str


class IngestedRule(BaseModel):
    title: str
    domain: str = Field(pattern="^(forex|lending|trading|bonds|general)$")
    type: str
    description: str = ""
    logic: str = Field(default="AND", pattern="^(AND|OR)$")
    conditions: conlist(IngestedCondition, min_length=1)
    action: IngestedAction
    severity: str = Field(default="medium")
    confidence: float = 1.0
    section: str = ""
    text_snippet: str = ""


@dataclass
class IngestResult:
    title: str
    file_path: str
    official_url: str
    status: str
    extracted: int = 0
    stored: int = 0
    skipped: int = 0
    detail: str | None = None


SEBI_PROMPT = """You are extracting executable SEBI compliance rules from reviewed official document text.

Return strict JSON only in this shape:
{{
    "rules": [
        {{
            "title": "short title",
            "domain": "trading|bonds|lending|forex|general",
            "type": "restriction|reporting|eligibility|threshold|obligation",
            "description": "one-line explanation",
            "logic": "AND|OR",
            "conditions": [
                {{"field": "snake_case", "operator": "==|!=|>|<|>=|<=|contains|in|not_in|exists", "value": "string|number|boolean|list"}}
            ],
            "action": {{"result": "allow|deny|flag|require", "message": "clear explanation"}},
            "severity": "low|medium|high|critical",
            "confidence": 0.0,
            "section": "section/clause reference if present",
            "text_snippet": "exact supporting sentence"
        }}
    ]
}}

Rules:
- Only return executable compliance rules with at least one concrete condition.
- Ignore definitions, notes, boilerplate, templates, and non-decision text.
- Prefer explicit SEBI disclosure, listing, intermediary, trading, and investor-eligibility obligations.
- If the text chunk has no executable rule, return {{"rules": []}}.
- Keep the list short and precise.
- Do not include markdown or commentary.

DOCUMENT TITLE:
{title}

OFFICIAL URL:
{official_url}

TEXT CHUNK {chunk_number}/{chunk_total}:
{content}
"""


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "sebi-rule"


def _load_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    documents = payload.get("documents", [])
    if not isinstance(documents, list):
        raise ValueError("Manifest documents must be a list")
    return documents


def _resolve_document_path(doc_root: Path, suggested_file: str) -> Path:
    candidate = (doc_root / suggested_file).resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Document not found: {candidate}")
    if candidate.suffix.lower() != ".pdf":
        raise ValueError(f"Unsupported SEBI file type: {candidate.suffix}")
    return candidate


def _read_pdf_text(file_path: Path, max_pages: int = 10, max_chars: int = 30000) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    pages = []
    total_chars = 0
    for page_index, page in enumerate(reader.pages):
        if page_index >= max_pages or total_chars >= max_chars:
            break
        text = page.extract_text() or ""
        if text.strip():
            cleaned = text.strip()
            pages.append(cleaned)
            total_chars += len(cleaned)
    content = "\n\n".join(pages).strip()
    if not content:
        raise ValueError(f"No extractable text found in {file_path}")
    return content


def _chunk_text(text: str, max_chars: int = 5000, overlap: int = 400) -> List[str]:
    cleaned = re.sub(r"\r\n", "\n", text).strip()
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def _parse_json_payload(content: str) -> Dict[str, Any]:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start < 0 or end <= start:
        return {"rules": []}
    try:
        return json.loads(content[start:end])
    except Exception:
        return {"rules": []}


def _extract_rules_for_chunk(title: str, official_url: str, chunk: str, chunk_number: int, chunk_total: int, use_mock: bool = False) -> List[Dict[str, Any]]:
    if use_mock:
        # Mock mode: generate synthetic rules for demonstration
        return _generate_mock_rules(title, chunk, chunk_number)
    
    if not os.getenv("MISTRAL_API_KEY"):
        logger.warning("Skipping SEBI extraction for %s because MISTRAL_API_KEY is not configured", title)
        return []

    try:
        client = get_mistral_client()
        prompt = SEBI_PROMPT.format(
            title=title,
            official_url=official_url,
            chunk_number=chunk_number,
            chunk_total=chunk_total,
            content=chunk,
        )
        response = client.chat.complete(
            model="mistral-small",
            messages=[{"role": "user", "content": prompt}],
        )
        payload = _parse_json_payload(response.choices[0].message.content or "")
        rules = payload.get("rules", [])
        if not isinstance(rules, list):
            return []
        return rules
    except Exception as exc:
        logger.warning("SEBI extraction skipped for %s chunk %s: %s", title, chunk_number, exc)
        return []


def _generate_mock_rules(title: str, chunk: str, chunk_number: int) -> List[Dict[str, Any]]:
    """Generate synthetic SEBI rules for demonstration without LLM."""
    # Extract keywords from chunk to determine relevance
    chunk_lower = chunk.lower()
    
    rules = []
    
    # Check for listing/disclosure keywords
    if any(keyword in chunk_lower for keyword in ["disclosure", "listing", "annual report", "board"]):
        rules.append({
            "title": f"Mandatory Disclosure - {title} Chunk {chunk_number}",
            "domain": "trading",
            "type": "reporting",
            "description": "Listed entities must disclose material information within specified timelines",
            "logic": "AND",
            "conditions": [
                {"field": "entity_type", "operator": "==", "value": "listed_company"},
                {"field": "information_type", "operator": "in", "value": ["material_event", "board_decision"]},
            ],
            "action": {"result": "require", "message": "Disclose information to stock exchange within 24 hours"},
            "severity": "high",
            "confidence": 0.85,
            "section": "SEBI LODR",
            "text_snippet": chunk[:100] if len(chunk) > 100 else chunk,
        })
    
    # Check for trading/transaction keywords
    if any(keyword in chunk_lower for keyword in ["trading", "transaction", "settlement", "margin"]):
        rules.append({
            "title": f"Transaction Settlement - {title} Chunk {chunk_number}",
            "domain": "trading",
            "type": "obligation",
            "description": "Transactions must settle within prescribed timeframe",
            "logic": "AND",
            "conditions": [
                {"field": "transaction_type", "operator": "==", "value": "securities_trading"},
                {"field": "settlement_status", "operator": "!=", "value": "settled"},
            ],
            "action": {"result": "flag", "message": "Monitor settlement to ensure timely completion"},
            "severity": "medium",
            "confidence": 0.75,
            "section": "Settlement Rules",
            "text_snippet": chunk[:100] if len(chunk) > 100 else chunk,
        })
    
    # Check for intermediary/compliance keywords
    if any(keyword in chunk_lower for keyword in ["intermediary", "broker", "compliance", "audit"]):
        rules.append({
            "title": f"Intermediary Compliance - {title} Chunk {chunk_number}",
            "domain": "general",
            "type": "obligation",
            "description": "Market intermediaries must maintain compliance with SEBI standards",
            "logic": "AND",
            "conditions": [
                {"field": "intermediary_registration", "operator": "exists", "value": True},
                {"field": "compliance_score", "operator": "<", "value": 100},
            ],
            "action": {"result": "flag", "message": "Intermediary compliance audit required"},
            "severity": "high",
            "confidence": 0.80,
            "section": "Intermediary Regulations",
            "text_snippet": chunk[:100] if len(chunk) > 100 else chunk,
        })
    
    # Check for investor protection keywords
    if any(keyword in chunk_lower for keyword in ["investor", "protection", "grievance", "compensation"]):
        rules.append({
            "title": f"Investor Protection Measure - {title} Chunk {chunk_number}",
            "domain": "general",
            "type": "eligibility",
            "description": "Investor grievances must be addressed within prescribed timeframe",
            "logic": "AND",
            "conditions": [
                {"field": "grievance_status", "operator": "==", "value": "filed"},
                {"field": "resolution_days", "operator": ">", "value": 30},
            ],
            "action": {"result": "flag", "message": "Escalate grievance for resolution"},
            "severity": "medium",
            "confidence": 0.78,
            "section": "Investor Protection",
            "text_snippet": chunk[:100] if len(chunk) > 100 else chunk,
        })
    
    # Always include at least one general governance rule
    if len(rules) == 0:
        rules.append({
            "title": f"SEBI Governance Rule - {title} Chunk {chunk_number}",
            "domain": "general",
            "type": "obligation",
            "description": "All market participants must comply with applicable SEBI regulations",
            "logic": "AND",
            "conditions": [
                {"field": "market_participant", "operator": "exists", "value": True},
            ],
            "action": {"result": "require", "message": "Maintain compliance with SEBI regulations"},
            "severity": "medium",
            "confidence": 0.70,
            "section": "General Governance",
            "text_snippet": chunk[:100] if len(chunk) > 100 else chunk,
        })
    
    return rules


def _normalize_rule(raw_rule: Dict[str, Any], official_url: str, title: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = IngestedRule.model_validate(raw_rule)
    except ValidationError as exc:
        logger.info("Skipping invalid extracted rule from %s: %s", title, exc)
        return None

    canonical_rule = {
        "logic": parsed.logic,
        "conditions": [condition.model_dump() for condition in parsed.conditions],
    }

    return {
        "rule_id": f"SEBI-{_slugify(title)}-{_slugify(parsed.title)}",
        "version": 1,
        "domain": parsed.domain,
        "type": parsed.type,
        "title": parsed.title,
        "description": parsed.description,
        "canonical_rule": json.dumps(canonical_rule),
        "action": parsed.action.result,
        "source_document": title,
        "source_page": None,
        "source_url": official_url,
        "regulator": "SEBI",
        "severity": parsed.severity,
        "confidence": parsed.confidence,
        "is_active": True,
    }


def _upsert_rule(db, rule_data: Dict[str, Any]) -> str:
    existing = (
        db.query(ComplianceRule)
        .filter(
            ComplianceRule.source_url == rule_data["source_url"],
            ComplianceRule.title == rule_data["title"],
            ComplianceRule.canonical_rule == rule_data["canonical_rule"],
        )
        .first()
    )
    if existing:
        return "skipped"

    version_query = (
        db.query(ComplianceRule.version)
        .filter(ComplianceRule.rule_id == rule_data["rule_id"])
        .order_by(ComplianceRule.version.desc())
        .first()
    )
    next_version = (version_query[0] if version_query else 0) + 1

    rule = ComplianceRule(
        rule_id=rule_data["rule_id"],
        version=next_version,
        domain=rule_data["domain"],
        type=rule_data["type"],
        title=rule_data["title"],
        description=rule_data["description"],
        canonical_rule=rule_data["canonical_rule"],
        action=rule_data["action"],
        source_document=rule_data["source_document"],
        source_page=rule_data["source_page"],
        source_url=rule_data["source_url"],
        regulator=rule_data["regulator"],
        severity=rule_data["severity"],
        is_active=rule_data["is_active"],
        confidence=rule_data["confidence"],
    )
    db.add(rule)
    return "stored"


def ingest_sebi_manifest(
    manifest_path: Path = DEFAULT_MANIFEST,
    doc_root: Path = DEFAULT_DOC_ROOT,
    limit: Optional[int] = None,
    dry_run: bool = False,
    use_mock: bool = False,
) -> Dict[str, Any]:
    """Ingest reviewed SEBI PDFs from a manifest into ComplianceRule rows.
    
    Args:
        manifest_path: Path to manifest.json
        doc_root: Root directory for PDF resolution
        limit: Max documents to process
        dry_run: If True, validate but don't persist
        use_mock: If True, generate synthetic rules without LLM (for testing)
    """
    manifest_path = manifest_path.resolve()
    doc_root = doc_root.resolve()

    documents = _load_manifest(manifest_path)
    results: List[Dict[str, Any]] = []
    totals = {"documents": 0, "extracted": 0, "stored": 0, "skipped": 0, "failed": 0}

    db = SessionLocal()
    try:
        for index, item in enumerate(documents, start=1):
            if limit is not None and totals["documents"] >= limit:
                break

            suggested_file = item.get("suggested_file")
            if not suggested_file:
                continue

            title = item.get("title") or item.get("id") or f"SEBI Document {index}"
            official_url = item.get("official_url")
            if not official_url:
                results.append({"title": title, "status": "failed", "detail": "Missing official URL"})
                totals["failed"] += 1
                continue

            try:
                file_path = _resolve_document_path(doc_root, suggested_file)
                text = _read_pdf_text(file_path)
                chunks = _chunk_text(text)
                totals["documents"] += 1

                document_result = {"title": title, "file_path": str(file_path), "official_url": official_url, "chunks": len(chunks), "status": "processed", "stored": 0, "skipped": 0, "failed": 0}
                for chunk_number, chunk in enumerate(chunks, start=1):
                    try:
                        extracted = _extract_rules_for_chunk(title, official_url, chunk, chunk_number, len(chunks), use_mock=use_mock)
                    except Exception as exc:
                        logger.error("SEBI extraction failed for %s chunk %s: %s", title, chunk_number, exc)
                        totals["failed"] += 1
                        document_result["failed"] += 1
                        continue

                    totals["extracted"] += len(extracted)
                    for raw_rule in extracted:
                        normalized = _normalize_rule(raw_rule, official_url=official_url, title=title)
                        if not normalized:
                            totals["skipped"] += 1
                            document_result["skipped"] += 1
                            continue

                        if dry_run:
                            totals["stored"] += 1
                            document_result["stored"] += 1
                            results.append({"title": title, "status": "dry_run", "rule_id": normalized["rule_id"], "rule_title": normalized["title"]})
                            continue

                        try:
                            outcome = _upsert_rule(db, normalized)
                            if outcome == "stored":
                                totals["stored"] += 1
                                document_result["stored"] += 1
                            else:
                                totals["skipped"] += 1
                                document_result["skipped"] += 1
                        except SQLAlchemyError as exc:
                            db.rollback()
                            totals["failed"] += 1
                            document_result["failed"] += 1
                            logger.error("SEBI persistence failed for %s: %s", title, exc)

                if not dry_run:
                    db.commit()
                results.append(document_result)
            except Exception as exc:
                db.rollback()
                totals["failed"] += 1
                results.append({"title": title, "file_path": str((doc_root / suggested_file).resolve()), "official_url": official_url, "status": "failed", "detail": str(exc)})
    finally:
        db.close()

    return {
        "manifest": str(manifest_path),
        "doc_root": str(doc_root),
        "dry_run": dry_run,
        "use_mock": use_mock,
        "totals": totals,
        "results": results,
    }
