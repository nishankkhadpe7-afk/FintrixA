"""
Multi-Rule Execution Engine with Database Integration

Evaluates multiple rules against input data and returns all matching rules.
Supports nested logical structures (AND/OR).
"""

from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Any, Optional
from database_pool import get_connection as get_pooled_connection


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    """
    Establish connection to PostgreSQL database.
    """
    return get_pooled_connection()


# ============================================================
# EVALUATION FUNCTIONS
# ============================================================

def evaluate_condition(condition: Dict[str, Any], input_data: Dict[str, Any]) -> bool:
    """
    Evaluate a single atomic condition.
    
    Args:
        condition: {"field": ..., "operator": ..., "value": ...}
        input_data: Input dictionary to evaluate against
    
    Returns:
        bool: True if condition matches, False otherwise
    """
    
    field = condition.get("field")
    operator = condition.get("operator")
    expected_value = condition.get("value")
    
    # Get input value (None if field missing)
    input_value = input_data.get(field)
    
    # Handle missing fields
    if input_value is None:
        return False
    
    try:
        if operator == "==":
            return input_value == expected_value
        elif operator == "!=":
            return input_value != expected_value
        elif operator == ">":
            return input_value > expected_value
        elif operator == "<":
            return input_value < expected_value
        elif operator == ">=":
            return input_value >= expected_value
        elif operator == "<=":
            return input_value <= expected_value
        elif operator == "contains":
            return str(expected_value).lower() in str(input_value).lower()
        elif operator == "exists":
            exists = input_value is not None and str(input_value).strip() != ""
            return exists if bool(expected_value) else not exists
        elif operator == "not_in":
            if not isinstance(expected_value, list):
                return True
            return input_value not in expected_value
        else:
            # Unknown operator: fail safely
            return False
    except (TypeError, ValueError):
        # Comparison failed (e.g., comparing incompatible types)
        return False


def evaluate_node(node: Dict[str, Any], input_data: Dict[str, Any]) -> bool:
    """
    Recursively evaluate a node (atomic condition or logical group).
    
    Node structure:
    - Atomic: {"field": ..., "operator": ..., "value": ...}
    - Group: {"logic": "AND"|"OR", "conditions": [...]}
    
    Args:
        node: Node to evaluate
        input_data: Input data
    
    Returns:
        bool: True if node evaluates to true
    """
    
    # Check if it's a logical group
    if isinstance(node, dict) and "logic" in node:
        logic = node.get("logic", "AND")
        conditions = node.get("conditions", [])
        
        if logic == "AND":
            # All conditions must be true
            return all(evaluate_node(c, input_data) for c in conditions)
        
        elif logic == "OR":
            # Any condition must be true
            return any(evaluate_node(c, input_data) for c in conditions)
        
        else:
            # Unknown logic operator
            return False
    
    # Atomic condition
    else:
        return evaluate_condition(node, input_data)


def evaluate_rule(rule: Dict[str, Any], input_data: Dict[str, Any]) -> bool:
    """
    Evaluate a complete rule.
    
    Rule structure:
    {
        "logic": "AND"|"OR",
        "conditions": [...]
    }
    
    Backward compatibility: if no logic field, assume AND.
    
    Args:
        rule: Rule with conditions
        input_data: Input data
    
    Returns:
        bool: True if rule matches
    """
    
    logic = rule.get("logic", "AND")
    conditions = rule.get("conditions", [])
    
    if logic == "AND":
        return all(evaluate_node(c, input_data) for c in conditions)
    elif logic == "OR":
        return any(evaluate_node(c, input_data) for c in conditions)
    else:
        return False


# ============================================================
# DATABASE OPERATIONS
# ============================================================

def fetch_active_rules(conn) -> List[Dict[str, Any]]:
    """
    Fetch the latest version of each rule from the database.
    
    Uses: SELECT DISTINCT ON (rule_id) ORDER BY rule_id, version DESC
    
    Args:
        conn: Database connection
    
    Returns:
        List of active rules with metadata
    """
    
    query = """
    SELECT DISTINCT ON (rule_id)
        rule_id,
        version,
        type,
        action,
        canonical_rule
    FROM rules
    WHERE COALESCE(is_active, TRUE) = TRUE
    ORDER BY rule_id, version DESC
    """
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(query)
    rules = cur.fetchall()
    cur.close()
    
    return rules


# ============================================================
# DEBUG FUNCTIONS (return result + trace)
# ============================================================

def evaluate_condition_debug(condition: Dict[str, Any], input_data: Dict[str, Any]) -> tuple:
    """
    Evaluate atomic condition with debug trace.
    
    Returns:
        (bool, trace_dict)
    """
    
    field = condition.get("field")
    operator = condition.get("operator")
    expected_value = condition.get("value")
    actual_value = input_data.get(field)
    
    # Result logic (same as original)
    if actual_value is None:
        result = False
    else:
        try:
            if operator == "==":
                result = actual_value == expected_value
            elif operator == "!=":
                result = actual_value != expected_value
            elif operator == ">":
                result = actual_value > expected_value
            elif operator == "<":
                result = actual_value < expected_value
            elif operator == ">=":
                result = actual_value >= expected_value
            elif operator == "<=":
                result = actual_value <= expected_value
            elif operator == "contains":
                result = str(expected_value).lower() in str(actual_value).lower()
            elif operator == "exists":
                exists = actual_value is not None and str(actual_value).strip() != ""
                result = exists if bool(expected_value) else not exists
            elif operator == "not_in":
                if not isinstance(expected_value, list):
                    result = True
                else:
                    result = actual_value not in expected_value
            else:
                result = False
        except (TypeError, ValueError):
            result = False
    
    # Build trace
    trace = {
        "type": "atomic",
        "field": field,
        "operator": operator,
        "expected": expected_value,
        "actual": actual_value,
        "result": result
    }
    
    return result, trace


def evaluate_node_debug(node: Dict[str, Any], input_data: Dict[str, Any]) -> tuple:
    """
    Recursively evaluate node with debug trace.
    
    Returns:
        (bool, trace_dict)
    """
    
    # Check if it's a logical group
    if isinstance(node, dict) and "logic" in node:
        logic = node.get("logic", "AND")
        conditions = node.get("conditions", [])
        
        # Evaluate all children
        child_results = []
        child_traces = []
        
        for child in conditions:
            child_result, child_trace = evaluate_node_debug(child, input_data)
            child_results.append(child_result)
            child_traces.append(child_trace)
        
        # Combine results
        if logic == "AND":
            result = all(child_results)
        elif logic == "OR":
            result = any(child_results)
        else:
            result = False
        
        # Build trace
        trace = {
            "type": "group",
            "logic": logic,
            "children": child_traces,
            "results": child_results,
            "final": result
        }
        
        return result, trace
    
    # Atomic condition
    else:
        return evaluate_condition_debug(node, input_data)


# ============================================================
# MULTI-RULE EXECUTION
# ============================================================

def evaluate_all_rules(conn, input_data: Dict[str, Any], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Evaluate all active rules against input data.
    
    Fetches latest version of each rule, evaluates, returns all matches.
    
    Args:
        conn: Database connection
        input_data: Input dictionary to evaluate against
        debug: If True, print detailed execution traces
    
    Returns:
        List of matching rules with metadata
    """
    
    matching_rules = []
    
    try:
        # Fetch all active rules
        active_rules = fetch_active_rules(conn)
        
        if debug:
            print(f"\n{'='*70}")
            print(f"EVALUATING {len(active_rules)} RULES")
            print(f"Input Data: {input_data}")
            print(f"{'='*70}\n")
        
        # Evaluate each rule
        for rule_record in active_rules:
            try:
                rule_id = rule_record["rule_id"]
                version = rule_record["version"]
                action = rule_record["action"]
                rule_type = rule_record["type"]
                
                # Parse canonical_rule (handle both dict and JSON string)
                canonical_rule = rule_record["canonical_rule"]
                if isinstance(canonical_rule, str):
                    canonical_rule = json.loads(canonical_rule)
                
                # Ensure backward compatibility
                if "logic" not in canonical_rule:
                    canonical_rule["logic"] = "AND"
                
                # Evaluate rule (with or without debug)
                if debug:
                    logic = canonical_rule.get("logic", "AND")
                    conditions = canonical_rule.get("conditions", [])
                    
                    # Evaluate all conditions with trace
                    child_results = []
                    child_traces = []
                    
                    for cond in conditions:
                        cond_result, cond_trace = evaluate_node_debug(cond, input_data)
                        child_results.append(cond_result)
                        child_traces.append(cond_trace)
                    
                    # Combine results
                    if logic == "AND":
                        matched = all(child_results)
                    elif logic == "OR":
                        matched = any(child_results)
                    else:
                        matched = False
                    
                    # Print trace
                    print(f"[Rule: {rule_id}]")
                    print(f"  Version: {version} | Type: {rule_type}")
                    print(f"  Result: {matched}")
                    print(f"  Trace:")
                    
                    trace_output = {
                        "root_logic": logic,
                        "conditions": child_traces,
                        "results": child_results,
                        "final": matched
                    }
                    
                    print(json.dumps(trace_output, indent=4))
                    print()
                
                else:
                    # Non-debug: use original logic
                    matched = evaluate_rule(canonical_rule, input_data)
                
                if matched:
                    matching_rules.append({
                        "rule_id": rule_id,
                        "version": version,
                        "type": rule_type,
                        "action": action,
                        "matched": True
                    })
            
            except Exception as e:
                # Log error but continue with other rules
                if debug:
                    print(f"⚠️  Error evaluating rule {rule_record.get('rule_id')}: {e}\n")
                else:
                    print(f"⚠️  Error evaluating rule {rule_record.get('rule_id')}: {e}")
                continue
        
        if debug:
            print(f"{'='*70}")
            print(f"SUMMARY: {len(matching_rules)} rules matched")
            print(f"{'='*70}\n")
    
    except Exception as e:
        # Database fetch error
        print(f"❌ Error fetching rules: {e}")
        return []
    
    return matching_rules


# ============================================================
# CONVENIENCE WRAPPER
# ============================================================

def execute_against_db(input_data: Dict[str, Any], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Execute all active rules against input data.
    
    Handles database connection lifecycle.
    
    Args:
        input_data: Input data to evaluate
        debug: If True, print detailed execution traces
    
    Returns:
        List of matching rules
    """
    
    conn = None
    try:
        conn = get_db_connection()
        results = evaluate_all_rules(conn, input_data, debug=debug)
        return results
    
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return []
    
    finally:
        if conn:
            conn.close()


# ============================================================
# BATCH EXECUTION
# ============================================================

def execute_batch(inputs: List[Dict[str, Any]], debug: bool = False) -> List[Dict[str, Any]]:
    """
    Execute multiple inputs against all rules.
    
    Returns results for each input.
    
    Args:
        inputs: List of input dictionaries
        debug: If True, print detailed execution traces
    
    Returns:
        List of execution results
    """
    
    results = []
    conn = None
    
    try:
        conn = get_db_connection()
        
        for idx, input_data in enumerate(inputs):
            try:
                if debug:
                    print(f"\n{'='*70}")
                    print(f"INPUT {idx}: {input_data}")
                    print(f"{'='*70}")
                
                matches = evaluate_all_rules(conn, input_data, debug=debug)
                
                results.append({
                    "input_idx": idx,
                    "input_data": input_data,
                    "matching_rules": matches,
                    "match_count": len(matches)
                })
            
            except Exception as e:
                print(f"⚠️  Error processing input {idx}: {e}")
                results.append({
                    "input_idx": idx,
                    "input_data": input_data,
                    "error": str(e),
                    "matching_rules": []
                })
                continue
    
    except Exception as e:
        print(f"❌ Batch execution failed: {e}")
        return []
    
    finally:
        if conn:
            conn.close()
    
    return results


# ============================================================
# AGGREGATION
# ============================================================

def aggregate_actions(matching_rules: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Aggregate actions from matching rules by type.
    
    Args:
        matching_rules: List of matching rules
    
    Returns:
        Dictionary mapping rule types to actions
    """
    
    aggregated = {}
    
    for rule in matching_rules:
        rule_type = rule.get("type", "unknown")
        action = rule.get("action", "unknown")
        
        if rule_type not in aggregated:
            aggregated[rule_type] = []
        
        aggregated[rule_type].append(action)
    
    return aggregated
