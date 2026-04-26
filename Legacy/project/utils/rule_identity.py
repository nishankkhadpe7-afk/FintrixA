import hashlib


def extract_fields(conditions):
    """Recursively extract field names from conditions (handles nested logical groups)."""
    fields = []
    for cond in conditions:
        if isinstance(cond, dict) and "logic" in cond:
            # Nested logical group — recurse into its conditions
            fields.extend(extract_fields(cond.get("conditions", [])))
        else:
            fields.append(cond.get("field", ""))
    return fields


def generate_rule_id(canonical_rule):
    """
    Generate stable rule identity (ignores values, focuses on structure)
    """

    identity_base = {
        "type": canonical_rule["type"],
        "action": canonical_rule["action"],
        "fields": sorted(extract_fields(canonical_rule["conditions"]))
    }

    identity_str = str(identity_base)

    return hashlib.md5(identity_str.encode()).hexdigest()[:12]