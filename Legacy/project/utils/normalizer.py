from copy import deepcopy
from utils.field_mapper import normalize_field


# 🔥 Operator normalization map (LLM → canonical)
OPERATOR_MAP = {
    "equals": "==",
    "=": "==",
    "==": "==",

    "not_equals": "!=",
    "not_equal": "!=",
    "!=": "!=",

    "greater_than": ">",
    "greater_than_equal": ">=",
    "greater_than_or_equal": ">=",
    "greater_than_or_equal_to": ">=",
    "less_than": "<",
    "less_than_equal": "<=",
    "less_than_or_equal": "<=",
    "less_than_or_equal_to": "<=",
    "less_than_or_equals": "<=",

    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
    "contains": "contains",
    "exists": "exists",
    "within": "in",
    "not_in": "not_in",
    "in": "in",
}


# ✅ Final allowed operators
ALLOWED_OPERATORS = {">", "<", ">=", "<=", "==", "!=", "contains", "exists"}

RULE_TYPE_MAP = {
    "definition": None,
    "applicability": None,
    "interpretation": None,
    "eligibility": "eligibility",
    "prohibition": "prohibition",
    "conditional": "conditional",
    "aggregation": "aggregation",
    "restriction": "restriction",
    "obligation": "obligation",
    "exception": "exception",
    "requirement": "obligation",
    "approval": "eligibility",
    "allowance": "eligibility",
}


# -------------------------------------------------------------------
# 🔹 STRING CANONICALIZATION
# -------------------------------------------------------------------

def canonicalize_string(value: str) -> str:
    return value.lower().strip().replace(" ", "_")


# -------------------------------------------------------------------
# 🔹 VALUE NORMALIZATION
# -------------------------------------------------------------------

def normalize_value(value):
    if isinstance(value, str):
        value = value.lower().strip()

        # ₹2 lakh → 200000
        if "lakh" in value:
            try:
                num = float(value.replace("lakh", "").strip())
                return int(num * 100000)
            except:
                pass

        # float
        try:
            if "." in value:
                return float(value)
        except:
            pass

        # int
        if value.isdigit():
            return int(value)

        return canonicalize_string(value)

    if isinstance(value, list):
        return [normalize_value(item) for item in value]

    return value


# -------------------------------------------------------------------
# 🔹 ATOMIC CONDITION
# -------------------------------------------------------------------

def normalize_condition(cond):
    if not all(k in cond for k in ("field", "operator")):
        raise ValueError(f"Invalid condition: {cond}")

    field = canonicalize_string(normalize_field(cond["field"]))

    raw_operator = cond["operator"].lower().strip()

    if raw_operator not in OPERATOR_MAP:
        raise ValueError(f"Unknown operator: {raw_operator}")

    operator = OPERATOR_MAP[raw_operator]

    if operator not in ALLOWED_OPERATORS:
        raise ValueError(f"Invalid operator: {operator}")

    if operator == "exists":
        raw_value = cond.get("value", True)
        normalized_flag = normalize_value(raw_value)
        value = normalized_flag not in {False, "false", "no", 0, "0"}
    else:
        if "value" not in cond:
            raise ValueError(f"Invalid condition: {cond}")
        value = normalize_value(cond["value"])

    return {
        "field": field,
        "operator": operator,
        "value": value
    }


# -------------------------------------------------------------------
# 🔹 NORMALIZE CONDITIONS LIST (WITH LOGIC SUPPORT)
# -------------------------------------------------------------------

def normalize_conditions_list(conditions):
    normalized = []

    for cond in conditions:
        if not cond:
            continue
        # 🔹 Nested logical group (future-proof)
        if isinstance(cond, dict) and "logic" in cond:
            logic = cond["logic"].upper()
            if logic not in ("AND", "OR"):
                raise ValueError(f"Invalid logic: {logic}")

            nested = normalize_conditions_list(cond.get("conditions", []))
            if not nested:
                continue

            normalized.append({
                "logic": logic,
                "conditions": nested
            })
            continue

        raw_operator = cond["operator"].lower().strip()

        # 🔥 IN → OR GROUP
        if raw_operator == "in" and isinstance(cond.get("value"), list):
            field = canonicalize_string(normalize_field(cond["field"]))

            values = sorted(set(normalize_value(v) for v in cond["value"]))

            or_group = {
                "logic": "OR",
                "conditions": [
                    {
                        "field": field,
                        "operator": "==",
                        "value": v
                    }
                    for v in values
                ]
            }

            normalized.append(or_group)
            continue

        # 🔥 NOT_IN → AND GROUP of !=
        if raw_operator == "not_in" and isinstance(cond.get("value"), list):
            field = canonicalize_string(normalize_field(cond["field"]))

            values = sorted(set(normalize_value(v) for v in cond["value"]))

            and_group = {
                "logic": "AND",
                "conditions": [
                    {
                        "field": field,
                        "operator": "!=",
                        "value": v
                    }
                    for v in values
                ]
            }

            normalized.append(and_group)
            continue

        # 🔹 Atomic
        normalized.append(normalize_condition(cond))

    return [item for item in normalized if item]


# -------------------------------------------------------------------
# 🔹 DETERMINISTIC SORTING (RECURSIVE)
# -------------------------------------------------------------------

def sort_conditions(conditions):
    def sort_key(item):
        if "logic" in item:
            return (1, item["logic"])
        return (
            0,
            item.get("field", ""),
            item.get("operator", ""),
            str(item.get("value", ""))
        )

    sorted_conds = sorted(conditions, key=sort_key)

    # recursive sort
    for item in sorted_conds:
        if "logic" in item:
            item["conditions"] = sort_conditions(item["conditions"])

    return sorted_conds


# -------------------------------------------------------------------
# 🔹 MAIN NORMALIZER
# -------------------------------------------------------------------

def normalize_rule(rule_dict):
    """
    Deterministic normalization:
    - No mutation
    - Logical structure preserved
    - Canonical values
    - Sorted conditions
    """

    rule = deepcopy(rule_dict)

    if "conditions" not in rule:
        raise ValueError("Rule missing conditions")

    normalized_conditions = normalize_conditions_list(rule["conditions"])
    if not normalized_conditions:
        raise ValueError("Rule has no executable conditions")
    sorted_conditions = sort_conditions(normalized_conditions)

    raw_action = rule.get("action", "")
    action_value = raw_action
    description = rule.get("description") or ""

    if isinstance(raw_action, dict):
        action_value = raw_action.get("result", "")
        description = description or raw_action.get("message", "")

    normalized_action = canonicalize_string(str(action_value or "flag"))
    action_map = {
        "allow": "allow",
        "eligible": "allow",
        "approve": "allow",
        "approved": "allow",
        "deny": "deny",
        "denied": "deny",
        "block": "deny",
        "blocked": "deny",
        "prohibit": "deny",
        "prohibited": "deny",
        "not_eligible_for_agency_commission": "deny",
        "flag": "flag",
        "review": "flag",
        "require": "flag",
        "required": "flag",
    }

    metadata = rule.get("metadata", {}) if isinstance(rule.get("metadata"), dict) else {}

    normalized_type = canonicalize_string(str(rule.get("type", "")))
    mapped_type = RULE_TYPE_MAP.get(normalized_type, normalized_type)
    if mapped_type is None:
        raise ValueError(f"Non-executable rule type: {normalized_type}")

    return {
        "type": mapped_type,
        "title": str(rule.get("title", "")).strip(),
        "description": str(description).strip(),
        "action": action_map.get(normalized_action, normalized_action or "flag"),
        "logic": str(rule.get("logic", "AND")).upper(),
        "conditions": sorted_conditions,
        "source_section": str(metadata.get("section", "")).strip(),
        "confidence_score": float(metadata.get("confidence", 1.0) or 1.0),
        "regulator": str(metadata.get("source", "")).strip(),
    }
