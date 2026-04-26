"""
Simulation service: evaluates multiple input scenarios against all active rules.

Uses a single DB connection for all inputs for efficiency.
"""

import json
import logging
import uuid
from typing import Any, Dict, List

from engine.executor import (
    get_db_connection,
    fetch_active_rules,
    evaluate_rule,
    evaluate_node_debug,
)
from api.core.exceptions import EngineError

logger = logging.getLogger(__name__)


def _humanize_rule_type(rule_type: str | None) -> str:
    if not rule_type:
        return "Regulatory"
    return str(rule_type).replace("_", " ").strip().title()


def _format_condition_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _build_rule_title(rule_record: Dict[str, Any], canonical_rule: Dict[str, Any]) -> str:
    title = canonical_rule.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    rule_type = _humanize_rule_type(rule_record.get("type"))
    action = str(rule_record.get("action", "FLAG")).title()
    conditions = canonical_rule.get("conditions", [])

    first_atomic = next(
        (
            condition
            for condition in conditions
            if isinstance(condition, dict) and "field" in condition and "operator" in condition
        ),
        None,
    )

    if first_atomic:
        field = str(first_atomic.get("field", "input")).replace("_", " ").title()
        operator = str(first_atomic.get("operator", "=="))
        value = _format_condition_value(first_atomic.get("value"))
        return f"{rule_type} {action}: {field} {operator} {value}"

    return f"{rule_type} {action} Rule"


def _build_rule_description(rule_record: Dict[str, Any], canonical_rule: Dict[str, Any]) -> str:
    description = canonical_rule.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()

    conditions = canonical_rule.get("conditions", [])
    if not conditions:
        return f"Matched {_humanize_rule_type(rule_record.get('type')).lower()} rule."

    summaries = []
    for condition in conditions[:2]:
        if isinstance(condition, dict) and "field" in condition and "operator" in condition:
            field = str(condition.get("field", "input")).replace("_", " ")
            operator = str(condition.get("operator", "=="))
            value = _format_condition_value(condition.get("value"))
            summaries.append(f"{field} {operator} {value}")

    if summaries:
        return "Matched because " + " and ".join(summaries) + "."

    return f"Matched {_humanize_rule_type(rule_record.get('type')).lower()} rule."


def simulate(
    inputs: List[Dict[str, Any]], debug: bool = False
) -> Dict[str, Any]:
    """
    Evaluate multiple input scenarios against all active rules.

    Args:
        inputs: List of input dictionaries
        debug: If True, include condition-level traces

    Returns:
        Structured simulation results
    """
    # Generate unique request ID for traceability
    request_id = str(uuid.uuid4())
    
    logger.info(f"[{request_id}] Simulation started: {len(inputs)} inputs")
    
    # Log each input for debugging
    for idx, input_data in enumerate(inputs):
        logger.info(f"[{request_id}] Input {idx}: {input_data}")
    
    conn = None

    try:
        conn = get_db_connection()
        active_rules = fetch_active_rules(conn)

        logger.info(f"[{request_id}] Fetched {len(active_rules)} active rules")

        results = []
        total_matches = 0

        for idx, input_data in enumerate(inputs):
            try:
                logger.info(f"[{request_id}] Evaluating input {idx}: {input_data}")
                
                item = _evaluate_input(
                    input_data, active_rules, debug=debug, request_id=request_id
                )
                results.append(item)
                total_matches += item["match_count"]
                
                logger.info(f"[{request_id}] Input {idx} matched {item['match_count']} rules")

            except Exception as e:
                logger.warning(f"[{request_id}] Input {idx}: evaluation failed — {e}")
                results.append({
                    "input": input_data,
                    "matched_rules": [],
                    "match_count": 0,
                })

        logger.info(f"[{request_id}] Simulation done: {total_matches} total matches across {len(inputs)} inputs")

        return {
            "request_id": request_id,
            "total_inputs": len(inputs),
            "total_matches": total_matches,
            "results": results,
        }

    except Exception as e:
        logger.error(f"[{request_id}] Simulation failed: {e}")
        raise EngineError(f"Simulation failed: {str(e)}")
    finally:
        if conn:
            conn.close()


def _evaluate_input(
    input_data: Dict[str, Any],
    active_rules: List[Dict[str, Any]],
    debug: bool = False,
    request_id: str = "",
) -> Dict[str, Any]:
    """
    Evaluate a single input against all pre-fetched rules.
    
    This function is STATELESS - it does not use any global state.
    Each evaluation is independent and uses only the provided input_data.
    """
    logger.info(f"[{request_id}] _evaluate_input called with: {input_data}")
    
    matched_rules = []
    traces = [] if debug else None

    for rule_record in active_rules:
        canonical_rule = rule_record["canonical_rule"]
        if isinstance(canonical_rule, str):
            canonical_rule = json.loads(canonical_rule)

        if "logic" not in canonical_rule:
            canonical_rule["logic"] = "AND"

        if debug:
            # Use debug evaluation to capture traces
            logic = canonical_rule.get("logic", "AND")
            conditions = canonical_rule.get("conditions", [])

            child_results = []
            child_traces = []
            for cond in conditions:
                cond_result, cond_trace = evaluate_node_debug(cond, input_data)
                child_results.append(cond_result)
                child_traces.append(cond_trace)

            matched = all(child_results) if logic == "AND" else any(child_results)

            traces.append({
                "rule_id": rule_record["rule_id"],
                "result": matched,
                "trace": {
                    "root_logic": logic,
                    "conditions": child_traces,
                    "results": child_results,
                    "final": matched,
                },
            })
        else:
            matched = evaluate_rule(canonical_rule, input_data)

        if matched:
            matched_rules.append({
                "rule_id": rule_record["rule_id"],
                "version": rule_record["version"],
                "type": rule_record["type"],
                "action": rule_record["action"],
                "title": _build_rule_title(rule_record, canonical_rule),
                "description": _build_rule_description(rule_record, canonical_rule),
            })

    result = {
        "input": input_data,  # CRITICAL: Return the exact input that was evaluated
        "matched_rules": matched_rules,
        "match_count": len(matched_rules),
    }

    if debug:
        result["trace"] = traces
    
    logger.info(f"[{request_id}] _evaluate_input result: {len(matched_rules)} rules matched")

    return result
