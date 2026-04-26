import json


def canonicalize_condition(cond):
    """
    Recursively canonicalize a condition (atom or group).
    """
    if isinstance(cond, dict) and "logic" in cond:
        # Group: recursively canonicalize nested conditions
        canonical_group = {
            "logic": cond["logic"],
            "conditions": [
                canonicalize_condition(c) for c in cond["conditions"]
            ]
        }
        # Sort nested conditions
        canonical_group["conditions"] = sorted(
            canonical_group["conditions"],
            key=lambda x: (
                x.get("logic", ""),  # Groups with logic field
                x.get("field", ""),  # Atoms with field
                x.get("operator", ""),
                str(x.get("value", ""))
            )
        )
        return canonical_group
    else:
        # Atomic condition: already normalized
        return cond


def canonicalize_rule(rule_dict):
    """
    Canonicalize rule:
    - Sort conditions recursively
    - Deduplicate if needed
    - Return deterministic structure
    """
    conditions = rule_dict["conditions"]
    
    # Recursively canonicalize each condition
    canonical_conditions = [
        canonicalize_condition(c) for c in conditions
    ]
    
    # Sort at root level
    canonical_conditions = sorted(
        canonical_conditions,
        key=lambda x: (
            x.get("logic", ""),
            x.get("field", ""),
            x.get("operator", ""),
            str(x.get("value", ""))
        )
    )

    canonical = {
        "type": rule_dict["type"],
        "action": rule_dict["action"],
        "logic": rule_dict.get("logic", "AND"),
        "conditions": canonical_conditions,
        "title": rule_dict.get("title", ""),
        "description": rule_dict.get("description", ""),
        "source_section": rule_dict.get("source_section", ""),
        "confidence_score": rule_dict.get("confidence_score", 1.0),
        "regulator": rule_dict.get("regulator", ""),
    }

    return canonical
