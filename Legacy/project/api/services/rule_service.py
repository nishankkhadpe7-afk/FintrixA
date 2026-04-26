"""
Service layer: wraps the core engine without modifying it.
"""

import json
import logging
from typing import Any, Dict, List

from engine.executor import (
    get_db_connection,
    fetch_active_rules,
    evaluate_rule,
    evaluate_node_debug,
)
from api.core.exceptions import EngineError, InvalidInputError

logger = logging.getLogger(__name__)


def evaluate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate input data against all active rules.

    Returns matched rules only.
    """
    if not input_data:
        raise InvalidInputError("Input data cannot be empty")

    conn = None
    try:
        conn = get_db_connection()
        active_rules = fetch_active_rules(conn)

        matching_rules = []

        for rule_record in active_rules:
            try:
                canonical_rule = rule_record["canonical_rule"]
                if isinstance(canonical_rule, str):
                    canonical_rule = json.loads(canonical_rule)

                if "logic" not in canonical_rule:
                    canonical_rule["logic"] = "AND"

                matched = evaluate_rule(canonical_rule, input_data)

                if matched:
                    matching_rules.append({
                        "rule_id": rule_record["rule_id"],
                        "version": rule_record["version"],
                        "type": rule_record["type"],
                        "action": rule_record["action"],
                        "matched": True,
                    })

            except Exception as e:
                logger.warning(f"Error evaluating rule {rule_record.get('rule_id')}: {e}")
                continue

        return {
            "matched_rules": [r["rule_id"] for r in matching_rules],
            "total_matches": len(matching_rules),
            "rules": matching_rules,
        }

    except (InvalidInputError, EngineError):
        raise
    except Exception as e:
        logger.error(f"Engine error during evaluation: {e}")
        raise EngineError(f"Evaluation failed: {str(e)}")
    finally:
        if conn:
            conn.close()


def evaluate_debug(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate input data against all active rules with full debug trace.

    Uses engine's evaluate_node_debug to capture structured traces
    instead of printing to stdout.
    """
    if not input_data:
        raise InvalidInputError("Input data cannot be empty")

    conn = None
    try:
        conn = get_db_connection()
        active_rules = fetch_active_rules(conn)

        all_rule_traces = []
        matching_rule_ids = []

        for rule_record in active_rules:
            try:
                rule_id = rule_record["rule_id"]
                version = rule_record["version"]
                action = rule_record["action"]
                rule_type = rule_record["type"]

                canonical_rule = rule_record["canonical_rule"]
                if isinstance(canonical_rule, str):
                    canonical_rule = json.loads(canonical_rule)

                if "logic" not in canonical_rule:
                    canonical_rule["logic"] = "AND"

                # Evaluate each condition with debug trace
                logic = canonical_rule.get("logic", "AND")
                conditions = canonical_rule.get("conditions", [])

                child_results = []
                child_traces = []

                for cond in conditions:
                    cond_result, cond_trace = evaluate_node_debug(cond, input_data)
                    child_results.append(cond_result)
                    child_traces.append(cond_trace)

                if logic == "AND":
                    matched = all(child_results)
                elif logic == "OR":
                    matched = any(child_results)
                else:
                    matched = False

                trace = {
                    "root_logic": logic,
                    "conditions": child_traces,
                    "results": child_results,
                    "final": matched,
                }

                all_rule_traces.append({
                    "rule_id": rule_id,
                    "version": version,
                    "type": rule_type,
                    "action": action,
                    "result": matched,
                    "trace": trace,
                })

                if matched:
                    matching_rule_ids.append(rule_id)

            except Exception as e:
                logger.warning(f"Error evaluating rule {rule_record.get('rule_id')}: {e}")
                continue

        return {
            "input_data": input_data,
            "total_rules_evaluated": len(active_rules),
            "matched_rules": matching_rule_ids,
            "total_matches": len(matching_rule_ids),
            "rules": all_rule_traces,
        }

    except (InvalidInputError, EngineError):
        raise
    except Exception as e:
        logger.error(f"Engine error during debug evaluation: {e}")
        raise EngineError(f"Debug evaluation failed: {str(e)}")
    finally:
        if conn:
            conn.close()


def list_rules() -> List[Dict[str, Any]]:
    """
    Return the latest version of each rule in a frontend-friendly shape.
    """
    conn = None
    try:
        conn = get_db_connection()
        active_rules = fetch_active_rules(conn)
        rules = []

        for rule_record in active_rules:
            canonical_rule = rule_record["canonical_rule"]
            if isinstance(canonical_rule, str):
                canonical_rule = json.loads(canonical_rule)

            rule_id = rule_record["rule_id"]
            action = rule_record["action"]
            rule_type = rule_record["type"]
            title = canonical_rule.get("title") or rule_id
            description = canonical_rule.get("description") or f"{rule_type} rule"

            rules.append({
                "id": rule_id,
                "title": title,
                "description": description,
                "conditions": canonical_rule.get("conditions", []),
                "action": action,
                "source_section": canonical_rule.get("source_section", rule_type),
                "confidence_score": canonical_rule.get("confidence_score", 1.0),
                "circular_id": canonical_rule.get("circular_id", "unknown-circular"),
                "created_at": canonical_rule.get("created_at"),
                "updated_at": canonical_rule.get("updated_at"),
                "full_json": canonical_rule,
            })

        return rules

    except Exception as e:
        logger.error(f"Rule listing failed: {e}")
        raise EngineError(f"Rule listing failed: {str(e)}")
    finally:
        if conn:
            conn.close()


def get_rule(rule_id: str) -> Dict[str, Any]:
    """
    Return a single latest-version rule by rule_id.
    """
    rules = list_rules()
    for rule in rules:
        if rule["id"] == rule_id:
            return rule
    raise InvalidInputError(f"Rule not found: {rule_id}")
