"""
Ingestion service: orchestrates the full rule extraction pipeline.

Pipeline: raw_text → extract → clean → normalize → validate → canonicalize → hash → store
"""

import json
import logging
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

from llm_parser import extract_rules
from api.core.exceptions import EngineError
from ingestion.manual_document_ingestion import ingest_local_document
from ingestion.rule_persistence import persist_extracted_rules

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def _get_connection():
    from config import DB_CONFIG
    return psycopg2.connect(**DB_CONFIG)


def _dict_cursor(connection):
    return connection.cursor(cursor_factory=RealDictCursor)


# ============================================================
# SINGLE TEXT INGESTION
# ============================================================

def ingest_rule(raw_text: str, source: str = "UNKNOWN") -> Dict[str, Any]:
    """
    Ingest raw regulatory text through the full pipeline.

    Returns:
        {
            "status": "success" | "partial" | "error",
            "rules": [...],
            "total_extracted": int,
            "total_stored": int,
            "total_skipped": int,
        }
    """

    # ---------------------------------------------------------
    # Step 1: LLM Extraction
    # ---------------------------------------------------------
    logger.info("Stage: LLM extraction started")

    try:
        raw_rules = extract_rules(raw_text)
    except Exception as e:
        logger.error(f"Stage: LLM extraction FAILED — {e}")
        raise EngineError(f"LLM extraction failed: {str(e)}")

    if not raw_rules:
        logger.warning("Stage: LLM extraction returned 0 rules")
        return {
            "status": "error",
            "rules": [],
            "total_extracted": 0,
            "total_stored": 0,
            "total_skipped": 0,
        }

    logger.info(f"Stage: LLM extraction OK — {len(raw_rules)} rules extracted")

    try:
        return persist_extracted_rules(raw_rules, source=source)
    except Exception as e:
        logger.error(f"Rule persistence failed: {e}")
        raise EngineError(f"Rule persistence failed: {str(e)}")


def list_circulars() -> List[Dict[str, Any]]:
    """
    Return ingested circulars from raw_documents for the frontend.
    """
    conn = None
    try:
        conn = _get_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            """
            SELECT id, title, url, content, published_date, created_at
            FROM raw_documents
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        cur.close()

        return [
            {
                "id": f"circ-{row['id']}",
                "title": row["title"],
                "date": row["published_date"].isoformat() if row["published_date"] else row["created_at"].isoformat(),
                "source_url": row["url"],
                "full_text": row["content"],
                "ingested_at": row["created_at"].isoformat(),
                "status": "active",
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Circular listing failed: {e}")
        raise EngineError(f"Circular listing failed: {str(e)}")
    finally:
        if conn:
            conn.close()


def get_circular(circular_id: str) -> Dict[str, Any]:
    circulars = list_circulars()
    for circular in circulars:
        if circular["id"] == circular_id:
            return circular
    raise EngineError(f"Circular not found: {circular_id}")


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Return basic ingestion stats for the dashboard.
    """
    conn = None
    try:
        conn = _get_connection()
        cur = _dict_cursor(conn)

        cur.execute("SELECT COUNT(*) AS total FROM raw_documents")
        total_circulars = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(DISTINCT rule_id) AS total FROM rules")
        total_rules = cur.fetchone()["total"]

        cur.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM processed_documents
            GROUP BY status
            """
        )
        status_counts = {row["status"]: row["total"] for row in cur.fetchall()}

        total_processed = sum(status_counts.values())
        success_count = status_counts.get("success", 0)
        failed_count = status_counts.get("failed", 0)

        cur.execute(
            """
            SELECT rd.id, rd.title, rd.created_at, COALESCE(jsonb_array_length(pd.result), 0) AS rules_extracted
            FROM raw_documents rd
            LEFT JOIN processed_documents pd ON pd.raw_document_id = rd.id
            ORDER BY rd.created_at DESC
            LIMIT 5
            """
        )
        recent_rows = cur.fetchall()
        cur.close()

        success_rate = (success_count / total_processed) if total_processed else 0.0
        failure_rate = (failed_count / total_processed) if total_processed else 0.0

        return {
            "total_circulars": total_circulars,
            "total_rules": total_rules,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "recent_ingestions": [
                {
                    "id": f"circ-{row['id']}",
                    "title": row["title"],
                    "ingested_at": row["created_at"].isoformat(),
                    "rules_extracted": row["rules_extracted"],
                }
                for row in recent_rows
            ],
        }
    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        raise EngineError(f"Dashboard stats failed: {str(e)}")
    finally:
        if conn:
            conn.close()


def ingest_manual_document(
    file_path: str,
    title: str,
    source: str = "SEBI",
    official_url: str | None = None,
    published_date: str | None = None,
) -> Dict[str, Any]:
    """
    Ingest a reviewed local file using the manual-document path.
    """
    try:
        return ingest_local_document(
            file_path=file_path,
            title=title,
            source=source,
            official_url=official_url,
            published_date=published_date,
        )
    except Exception as e:
        logger.error(f"Manual document ingestion failed: {e}")
        raise EngineError(f"Manual document ingestion failed: {str(e)}")
