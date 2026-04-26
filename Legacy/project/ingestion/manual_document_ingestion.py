"""
Manual document ingestion for regulator documents stored locally.

This is intended for sources such as SEBI where broad crawling may be unreliable,
but official documents can still be ingested from reviewed local files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ingestion.deduplicator import is_llm_processed
from ingestion.raw_store import store_raw_document
from ingestion.llm_extractor import extract_rules_from_content
from ingestion.database import get_connection, init_schema
from ingestion.rule_persistence import persist_extracted_rules
from ingestion.source_validation import validate_regulator_url

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANUAL_DOCS_ROOT = PROJECT_ROOT / "documents"


def _ensure_safe_path(file_path: str) -> Path:
    candidate = Path(file_path).expanduser()
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    resolved = candidate
    allowed_roots = [PROJECT_ROOT.resolve(), MANUAL_DOCS_ROOT.resolve()]

    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise ValueError(
            f"File path must be inside {PROJECT_ROOT} or {MANUAL_DOCS_ROOT}"
        )

    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Document file not found: {resolved}")

    return resolved


def _read_document_content(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md", ".html", ".htm"}:
        return path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:
            raise ValueError(
                "PDF ingestion requires the 'pypdf' package. "
                "Install it or convert the PDF to text first."
            ) from exc

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        content = "\n".join(page.strip() for page in pages if page.strip())
        if not content.strip():
            raise ValueError(f"No extractable text found in PDF: {path}")
        return content

    raise ValueError(
        f"Unsupported file type '{suffix}'. Use .txt, .md, .html, or .pdf."
    )


def _record_processing(
    url: str,
    raw_document_id: int,
    status: str,
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO processed_documents (raw_document_id, url, status, result, error)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET
                status = EXCLUDED.status,
                result = EXCLUDED.result,
                error = EXCLUDED.error,
                processed_at = NOW()
            """,
            (
                raw_document_id,
                url,
                status,
                json.dumps(result) if result else None,
                error,
            ),
        )
        conn.commit()
        cur.close()
    finally:
        if conn:
            conn.close()


def ingest_local_document(
    file_path: str,
    title: str,
    source: str = "SEBI",
    official_url: Optional[str] = None,
    published_date: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Ingest a reviewed local regulator document using the existing extraction pipeline.
    """
    init_schema()

    resolved_path = _ensure_safe_path(file_path)
    content = _read_document_content(resolved_path)

    if official_url:
        document_url = validate_regulator_url(official_url, source=source)
    else:
        document_url = f"local://{source.lower()}/{resolved_path.name}"

    if is_llm_processed(document_url) and not force:
        return {
            "status": "skipped",
            "source": source,
            "title": title,
            "url": document_url,
            "rules": [],
            "total_extracted": 0,
            "detail": "Document already processed successfully",
        }

    stored = store_raw_document(
        source=source,
        title=title,
        url=document_url,
        content=content,
        published_date=published_date,
    )

    if not stored:
        return {
            "status": "skipped",
            "source": source,
            "title": title,
            "url": document_url,
            "rules": [],
            "total_extracted": 0,
            "detail": "Document storage skipped",
        }

    try:
        rules = extract_rules_from_content(content, url=document_url)
        persistence = persist_extracted_rules(rules or [], source=source)
        status = "success" if rules else "failed"
        error = None if rules else "No rules extracted"
        _record_processing(
            url=document_url,
            raw_document_id=stored["id"],
            status=status,
            result=rules,
            error=error,
        )

        return {
            "status": status,
            "source": source,
            "title": title,
            "url": document_url,
            "file_path": str(resolved_path),
            "forced": force,
            "rules": rules or [],
            "total_extracted": len(rules or []),
            "total_stored": persistence.get("total_stored", 0),
            "total_skipped": persistence.get("total_skipped", 0),
            "stored_rules": persistence.get("rules", []),
            "detail": error,
        }

    except Exception as exc:
        logger.error(f"Manual ingestion failed for {resolved_path}: {exc}")
        _record_processing(
            url=document_url,
            raw_document_id=stored["id"],
            status="failed",
            result=None,
            error=str(exc),
        )
        raise
