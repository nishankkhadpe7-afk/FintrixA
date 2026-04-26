"""
Shared persistence helpers for validated rule insertion.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import psycopg2

from config import DB_CONFIG
from models.rule_model import Rule
from utils.canonicalizer import canonicalize_rule
from utils.cleaner import clean_llm_output
from utils.hasher import generate_rule_hash
from utils.normalizer import normalize_rule
from utils.rule_identity import generate_rule_id

logger = logging.getLogger(__name__)


class SkippedRuleError(ValueError):
    """Raised when an extracted item is not an executable rule."""
    pass


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def process_rule_dict(rule_dict: Dict[str, Any] | str) -> Dict[str, Any]:
    cleaned = clean_llm_output(rule_dict) if isinstance(rule_dict, str) else rule_dict
    try:
        normalized = normalize_rule(cleaned)
    except ValueError as exc:
        message = str(exc)
        if "Non-executable rule type" in message or "no executable conditions" in message:
            raise SkippedRuleError(message) from exc
        raise
    validated = Rule(**normalized).model_dump()
    return canonicalize_rule(validated)


def store_canonical_rule(
    conn,
    canonical: Dict[str, Any],
    source: str = "UNKNOWN",
) -> Dict[str, Any]:
    rule_hash = generate_rule_hash(canonical)
    rule_id = generate_rule_id(canonical)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM rules WHERE rule_hash = %s", (rule_hash,))
        if cur.fetchone():
            return {
                "status": "skipped",
                "rule_id": rule_id,
                "rule_hash": rule_hash,
                "detail": "Duplicate rule - hash already exists",
            }

        cur.execute("SELECT MAX(version) FROM rules WHERE rule_id = %s", (rule_id,))
        result = cur.fetchone()[0]
        new_version = (result or 0) + 1

        cur.execute(
            """
            INSERT INTO rules (
                rule_hash, rule_id, version, type, title,
                regulator, action, description, canonical_rule
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                rule_hash,
                rule_id,
                new_version,
                canonical.get("type"),
                canonical.get("title", "") or rule_id,
                canonical.get("regulator") or source,
                canonical.get("action"),
                canonical.get("description", ""),
                json.dumps(canonical),
            ),
        )
        db_id = cur.fetchone()[0]

        for cond in canonical.get("conditions", []):
            if "field" in cond:
                cur.execute(
                    """
                    INSERT INTO conditions (rule_id, field, operator, value)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (db_id, cond["field"], cond["operator"], json.dumps(cond["value"])),
                )

        conn.commit()
        return {
            "status": "stored",
            "rule_id": rule_id,
            "rule_hash": rule_hash,
            "version": new_version,
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def persist_extracted_rules(
    raw_rules: List[Dict[str, Any]],
    source: str = "UNKNOWN",
) -> Dict[str, Any]:
    if not raw_rules:
        return {
            "status": "error",
            "rules": [],
            "total_extracted": 0,
            "total_stored": 0,
            "total_skipped": 0,
        }

    conn = None
    results = []
    stored_count = 0
    skipped_count = 0

    try:
        conn = get_connection()
        for idx, rule_dict in enumerate(raw_rules, start=1):
            try:
                canonical = process_rule_dict(rule_dict)
                result = store_canonical_rule(conn, canonical, source=source)
                results.append(result)
                if result["status"] == "stored":
                    stored_count += 1
                elif result["status"] == "skipped":
                    skipped_count += 1
            except SkippedRuleError as exc:
                logger.info("Rule %s skipped: %s", idx, exc)
                skipped_count += 1
                results.append({"status": "skipped", "detail": str(exc)})
            except Exception as exc:
                logger.error("Rule %s persistence failed: %s", idx, exc)
                results.append({"status": "error", "detail": str(exc)})
    finally:
        if conn:
            conn.close()

    status = "success" if stored_count > 0 else ("skipped" if skipped_count else "error")
    return {
        "status": status,
        "rules": results,
        "total_extracted": len(raw_rules),
        "total_stored": stored_count,
        "total_skipped": skipped_count,
    }
