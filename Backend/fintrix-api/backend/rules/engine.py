"""
Integrated Fintrix-style rule evaluation engine for S92.

Evaluates structured canonical rules with AND/OR logic,
provides normalized match payloads, and stores audit traces.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.rules.models import ComplianceRule, RuleEvaluation


SEVERITY_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

ACTION_STATUS = {
    "allow": "Compliant",
    "flag": "Review Required",
    "review": "Review Required",
    "block": "Non-Compliant",
}

ACTION_RISK = {
    "allow": "Low",
    "flag": "Medium",
    "review": "High",
    "block": "High",
}

SEVERITY_RISK = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "High",
}


def evaluate_condition(condition: Dict[str, Any], input_data: Dict[str, Any]) -> bool:
    """Evaluate a single atomic condition against input data."""
    field = condition.get("field")
    operator = condition.get("operator")
    expected_value = condition.get("value")
    input_value = input_data.get(field)

    if input_value is None:
        return False

    try:
        if operator == "==":
            return input_value == expected_value
        if operator == "!=":
            return input_value != expected_value
        if operator == ">":
            return float(input_value) > float(expected_value)
        if operator == "<":
            return float(input_value) < float(expected_value)
        if operator == ">=":
            return float(input_value) >= float(expected_value)
        if operator == "<=":
            return float(input_value) <= float(expected_value)
        if operator == "contains":
            return str(expected_value).lower() in str(input_value).lower()
        if operator == "not_contains":
            return str(expected_value).lower() not in str(input_value).lower()
        if operator == "in":
            if isinstance(expected_value, list):
                return input_value in expected_value
            return str(input_value) in str(expected_value)
        if operator == "not_in":
            if isinstance(expected_value, list):
                return input_value not in expected_value
            return str(input_value) not in str(expected_value)
        if operator == "exists":
            exists = input_value is not None and str(input_value).strip() != ""
            return exists if bool(expected_value) else not exists
        if operator == "between":
            if isinstance(expected_value, list) and len(expected_value) == 2:
                return float(expected_value[0]) <= float(input_value) <= float(expected_value[1])
            return False
        return False
    except (TypeError, ValueError):
        return False


def evaluate_node(node: Dict[str, Any], input_data: Dict[str, Any]) -> bool:
    """Recursively evaluate a node (atomic condition or logical group)."""
    if isinstance(node, dict) and "logic" in node:
        logic = str(node.get("logic", "AND")).upper()
        conditions = node.get("conditions", [])
        if logic == "AND":
            return all(evaluate_node(child, input_data) for child in conditions)
        if logic == "OR":
            return any(evaluate_node(child, input_data) for child in conditions)
        return False
    return evaluate_condition(node, input_data)


def evaluate_condition_debug(condition: Dict[str, Any], input_data: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    """Evaluate an atomic condition and return a trace payload."""
    field = condition.get("field")
    operator = condition.get("operator")
    expected_value = condition.get("value")
    actual_value = input_data.get(field)
    result = evaluate_condition(condition, input_data)
    trace = {
        "type": "atomic",
        "field": field,
        "operator": operator,
        "expected": expected_value,
        "actual": actual_value,
        "result": result,
    }
    return result, trace


def evaluate_node_debug(node: Dict[str, Any], input_data: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    """Recursively evaluate a rule node and return structured trace data."""
    if isinstance(node, dict) and "logic" in node:
        logic = str(node.get("logic", "AND")).upper()
        conditions = node.get("conditions", [])
        child_results = []
        child_traces = []
        for child in conditions:
            child_result, child_trace = evaluate_node_debug(child, input_data)
            child_results.append(child_result)
            child_traces.append(child_trace)
        result = all(child_results) if logic == "AND" else any(child_results) if logic == "OR" else False
        trace = {
            "type": "group",
            "logic": logic,
            "children": child_traces,
            "results": child_results,
            "final": result,
        }
        return result, trace
    return evaluate_condition_debug(node, input_data)


def fetch_active_rules(db: Session, domain: Optional[str] = None) -> List[ComplianceRule]:
    """Fetch active rules, optionally filtered by domain."""
    query = db.query(ComplianceRule).filter(ComplianceRule.is_active == True)  # noqa: E712
    if domain:
        query = query.filter(ComplianceRule.domain == domain.lower())
    return query.order_by(ComplianceRule.domain, ComplianceRule.rule_id).all()


def normalize_rule_match(rule: ComplianceRule, matched: bool, trace_output: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalize a matched rule into a stable frontend/API payload."""
    canonical_rule = {}
    try:
        canonical_rule = json.loads(rule.canonical_rule) if rule.canonical_rule else {}
    except json.JSONDecodeError:
        canonical_rule = {}

    return {
        "id": rule.id,
        "rule_id": rule.rule_id,
        "version": rule.version,
        "title": rule.title,
        "description": rule.description,
        "domain": rule.domain,
        "type": rule.type,
        "action": rule.action,
        "severity": rule.severity,
        "regulator": rule.regulator,
        "source_document": rule.source_document,
        "source_url": rule.source_url,
        "source_page": rule.source_page,
        "confidence": rule.confidence,
        "matched": matched,
        "canonical_rule": canonical_rule,
        "trace": trace_output,
    }


def summarize_rule_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a compact summary and decision posture from a normalized rule result."""
    matched_rules = result.get("matched_rules", [])
    total_rules = int(result.get("total_rules", 0) or 0)

    if not matched_rules:
        return {
            "status": "Compliant",
            "risk_level": "Low",
            "highest_severity": None,
            "triggered_actions": [],
            "matched_rule_ids": [],
            "matched_rule_titles": [],
            "summary": f"No active rule violations detected across {total_rules} rules checked.",
            "reason": "No active compliance rules were triggered by the scenario.",
        }

    sorted_matches = sorted(
        matched_rules,
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity", "low")).lower(), -1),
            SEVERITY_ORDER.get(str(item.get("action", "allow")).lower(), -1),
        ),
        reverse=True,
    )
    top_match = sorted_matches[0]
    highest_severity = str(top_match.get("severity", "medium")).lower()
    triggered_actions = sorted({str(item.get("action", "flag")).lower() for item in matched_rules})

    if "block" in triggered_actions:
        status = "Non-Compliant"
    elif "review" in triggered_actions or "flag" in triggered_actions:
        status = "Review Required"
    else:
        status = ACTION_STATUS.get(str(top_match.get("action", "allow")).lower(), "Compliant")

    risk_level = SEVERITY_RISK.get(highest_severity, ACTION_RISK.get(str(top_match.get("action", "flag")).lower(), "Medium"))
    titles = [str(item.get("title", item.get("rule_id", "Rule"))) for item in matched_rules[:3]]
    rule_refs = ", ".join(str(item.get("rule_id")) for item in matched_rules[:3] if item.get("rule_id"))
    title_text = "; ".join(titles)
    reason = f"Triggered {len(matched_rules)} rule(s): {title_text}."
    summary = f"{status}: {len(matched_rules)} rule(s) matched out of {total_rules} checked"
    if rule_refs:
        summary += f" ({rule_refs})"
    summary += "."

    return {
        "status": status,
        "risk_level": risk_level,
        "highest_severity": highest_severity,
        "triggered_actions": triggered_actions,
        "matched_rule_ids": [item.get("rule_id") for item in matched_rules if item.get("rule_id")],
        "matched_rule_titles": [item.get("title") for item in matched_rules if item.get("title")],
        "summary": summary,
        "reason": reason,
    }


def _build_rule_trace(rule: ComplianceRule, canonical_rule: Dict[str, Any], input_data: Dict[str, Any], debug: bool) -> tuple[bool, Optional[Dict[str, Any]]]:
    """Evaluate a rule and optionally produce a trace payload."""
    if "logic" not in canonical_rule:
        canonical_rule["logic"] = "AND"

    if debug:
        matched, root_trace = evaluate_node_debug(canonical_rule, input_data)
        trace_output = {
            "rule_id": rule.rule_id,
            "rule_title": rule.title,
            "root_logic": canonical_rule.get("logic", "AND"),
            "trace": root_trace,
            "final": matched,
        }
        return matched, trace_output

    matched = evaluate_node(canonical_rule, input_data)
    return matched, None


def evaluate_all_rules(
    db: Session,
    input_data: Dict[str, Any],
    domain: Optional[str] = None,
    debug: bool = False,
    source: str = "manual",
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Evaluate all active rules against input data and return a normalized payload."""
    active_rules = fetch_active_rules(db, domain)
    matched_rules: List[Dict[str, Any]] = []
    all_traces: List[Dict[str, Any]] = []

    for rule in active_rules:
        try:
            canonical_rule = json.loads(rule.canonical_rule)
            matched, trace_output = _build_rule_trace(rule, canonical_rule, input_data, debug)

            if matched:
                matched_rules.append(normalize_rule_match(rule, matched=True, trace_output=trace_output if debug else None))

            if debug and trace_output:
                all_traces.append(trace_output)

            try:
                evaluation_trace = trace_output or {
                    "rule_id": rule.rule_id,
                    "rule_title": rule.title,
                    "final": matched,
                }
                evaluation_log = RuleEvaluation(
                    user_id=user_id,
                    rule_id=rule.rule_id,
                    input_summary=json.dumps(input_data)[:1000],
                    matched=matched,
                    trace=json.dumps(evaluation_trace),
                    source=source,
                )
                db.add(evaluation_log)
            except Exception:
                pass
        except Exception as exc:
            print(f"Error evaluating rule {rule.rule_id}: {exc}")
            continue

    try:
        db.commit()
    except Exception:
        db.rollback()

    result = {
        "total_rules": len(active_rules),
        "match_count": len(matched_rules),
        "matched_rules": matched_rules,
        "input_data": input_data,
    }
    if debug:
        result["traces"] = all_traces
    result["rule_summary"] = summarize_rule_result(result)
    return result


def simulate_rules(
    db: Session,
    inputs: List[Dict[str, Any]],
    domain: Optional[str] = None,
    debug: bool = False,
    source: str = "simulation",
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Evaluate multiple inputs and return a stable simulator payload."""
    request_id = str(uuid.uuid4())
    results: List[Dict[str, Any]] = []
    total_matches = 0

    for input_data in inputs:
        evaluation = evaluate_all_rules(
            db=db,
            input_data=input_data,
            domain=domain or input_data.get("domain"),
            debug=debug,
            source=source,
            user_id=user_id,
        )
        results.append(
            {
                "input": evaluation.get("input_data", input_data),
                "matched_rules": evaluation.get("matched_rules", []),
                "match_count": evaluation.get("match_count", 0),
                "trace": evaluation.get("traces") if debug else None,
                "rule_summary": evaluation.get("rule_summary", {}),
            }
        )
        total_matches += int(evaluation.get("match_count", 0) or 0)

    return {
        "request_id": request_id,
        "total_inputs": len(inputs),
        "total_matches": total_matches,
        "results": results,
    }


def evaluate_for_scenario(
    db: Session,
    question: str,
    event_types: List[str],
    amount: int = 0,
    user_id: Optional[int] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Evaluate rules for an AI or What-If scenario.
    Converts scenario parameters into structured input for the rule engine.
    """
    input_data = {
        "question": question.lower(),
        "amount": amount,
        "event_types": event_types,
    }

    for event in event_types:
        input_data[f"event_{event}"] = True

    q = question.lower()
    if any(word in q for word in ["forex", "foreign", "lrs", "remittance", "transfer abroad", "abroad", "international transfer"]):
        input_data["domain"] = "forex"
    elif any(word in q for word in ["loan", "emi", "credit", "npa", "default", "lending"]):
        input_data["domain"] = "lending"
    elif any(word in q for word in ["stock", "share", "trading", "sebi", "insider"]):
        input_data["domain"] = "trading"
    elif any(word in q for word in ["bond", "debenture", "fixed income"]):
        input_data["domain"] = "bonds"
    else:
        input_data["domain"] = "general"

    input_data["declared"] = not any(
        phrase in q
        for phrase in [
            "undeclared",
            "unreported",
            "without declaring",
            "without declaration",
            "without reporting",
            "not declared",
            "not reported",
        ]
    )
    if any(word in q for word in ["fraud", "scam", "phishing", "unauthorized"]):
        input_data["fraud_indicator"] = True

    return evaluate_all_rules(
        db=db,
        input_data=input_data,
        debug=debug,
        source="scenario",
        user_id=user_id,
    )


def get_trace_history(db: Session, rule_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
    """Return recent evaluation traces in a UI-friendly shape."""
    query = db.query(RuleEvaluation)
    if rule_id:
        query = query.filter(RuleEvaluation.rule_id == rule_id)

    evaluations = query.order_by(RuleEvaluation.created_at.desc()).limit(limit).all()
    history = []
    for evaluation in evaluations:
        try:
            parsed_trace = json.loads(evaluation.trace) if evaluation.trace else {}
        except json.JSONDecodeError:
            parsed_trace = {"raw": evaluation.trace}

        try:
            parsed_input = json.loads(evaluation.input_summary) if evaluation.input_summary else {}
        except json.JSONDecodeError:
            parsed_input = {"raw": evaluation.input_summary}

        history.append(
            {
                "id": evaluation.id,
                "rule_id": evaluation.rule_id,
                "matched": evaluation.matched,
                "source": evaluation.source,
                "input_summary": parsed_input,
                "trace": parsed_trace,
                "created_at": str(evaluation.created_at),
            }
        )
    return history


def get_rule_stats(db: Session) -> Dict[str, Any]:
    """Get aggregate statistics about active rules and evaluations."""
    from sqlalchemy import func

    total = db.query(ComplianceRule).count()
    active = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).count()  # noqa: E712

    domain_counts = dict(
        db.query(ComplianceRule.domain, func.count(ComplianceRule.id))
        .filter(ComplianceRule.is_active == True)
        .group_by(ComplianceRule.domain)
        .all()
    )
    regulator_counts = dict(
        db.query(ComplianceRule.regulator, func.count(ComplianceRule.id))
        .filter(ComplianceRule.is_active == True)
        .group_by(ComplianceRule.regulator)
        .all()
    )
    severity_counts = dict(
        db.query(ComplianceRule.severity, func.count(ComplianceRule.id))
        .filter(ComplianceRule.is_active == True)
        .group_by(ComplianceRule.severity)
        .all()
    )
    eval_count = db.query(RuleEvaluation).count()

    return {
        "total_rules": total,
        "active_rules": active,
        "domains": domain_counts,
        "regulators": regulator_counts,
        "severities": severity_counts,
        "total_evaluations": eval_count,
    }
