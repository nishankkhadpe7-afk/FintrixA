def index_conditions(conditions):
    return {c["field"]: c for c in conditions if "field" in c}


def diff_rules(rule_v1, rule_v2):
    c1 = index_conditions(rule_v1["conditions"])
    c2 = index_conditions(rule_v2["conditions"])

    all_fields = set(c1.keys()) | set(c2.keys())

    changes = []

    for field in sorted(all_fields):  # deterministic order
        cond1 = c1.get(field)
        cond2 = c2.get(field)

        # -------------------------
        # ADDED
        # -------------------------
        if cond1 is None:
            changes.append({
                "type": "ADDED",
                "field": field,
                "new": cond2
            })
            continue

        # -------------------------
        # REMOVED
        # -------------------------
        if cond2 is None:
            changes.append({
                "type": "REMOVED",
                "field": field,
                "old": cond1
            })
            continue

        # -------------------------
        # MODIFIED
        # -------------------------
        operator_changed = cond1["operator"] != cond2["operator"]
        value_changed = cond1["value"] != cond2["value"]

        if operator_changed or value_changed:
            change = {
                "type": "MODIFIED",
                "field": field
            }

            # only include operator if changed
            if operator_changed:
                change["operator"] = {
                    "from": cond1["operator"],
                    "to": cond2["operator"]
                }

            # only include value if changed
            if value_changed:
                change["value"] = {
                    "from": cond1["value"],
                    "to": cond2["value"]
                }

            changes.append(change)

    return {"changes": changes}