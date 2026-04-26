def evaluate_condition(condition, input_data):
    """
    Evaluate a single atomic condition against input data.
    """
    field = condition["field"]
    operator = condition["operator"]
    value = condition["value"]

    input_value = input_data.get(field)

    if operator == "==":
        return input_value == value
    elif operator == "!=":
        return input_value != value
    elif operator == ">":
        return input_value > value
    elif operator == "<":
        return input_value < value
    elif operator == ">=":
        return input_value >= value
    elif operator == "<=":
        return input_value <= value
    else:
        raise ValueError(f"Unsupported operator: {operator}")


def evaluate_node(node, input_data):
    """
    Recursively evaluate a node (atomic condition or logical group).
    
    Node structure:
    - Atomic: {"field": ..., "operator": ..., "value": ...}
    - Group: {"logic": "AND"|"OR", "conditions": [...]}
    """
    
    # 🔹 Check if it's a logical group
    if isinstance(node, dict) and "logic" in node:
        logic = node["logic"]
        conditions = node.get("conditions", [])
        
        if logic == "AND":
            # All conditions must be true
            return all(evaluate_node(c, input_data) for c in conditions)
        
        elif logic == "OR":
            # Any condition must be true
            return any(evaluate_node(c, input_data) for c in conditions)
        
        else:
            raise ValueError(f"Unknown logic operator: {logic}")
    
    # 🔹 Atomic condition
    else:
        return evaluate_condition(node, input_data)


def evaluate_rule(rule, input_data):
    """
    Evaluate a complete rule against input data.
    
    Rule structure:
    {
        "type": "...",
        "action": "...",
        "logic": "AND"|"OR",
        "conditions": [...]
    }
    """
    
    # 🔹 Backward compatibility: if no logic field, assume AND
    logic = rule.get("logic", "AND")
    conditions = rule.get("conditions", [])
    
    if logic == "AND":
        return all(evaluate_node(c, input_data) for c in conditions)
    elif logic == "OR":
        return any(evaluate_node(c, input_data) for c in conditions)
    else:
        raise ValueError(f"Unknown logic operator: {logic}")


def execute_rule(rule, input_data):
    """
    Execute a rule: if conditions match, return action; else None.
    
    Args:
        rule: Normalized rule with logical structure
        input_data: Input dictionary to evaluate against
    
    Returns:
        action (str) if rule matches, None otherwise
    """
    
    if evaluate_rule(rule, input_data):
        return rule.get("action")
    
    return None