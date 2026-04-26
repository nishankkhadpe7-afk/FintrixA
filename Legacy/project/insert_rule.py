import json
from utils.rule_identity import generate_rule_id
from utils.diff_engine import diff_rules
from db import get_rule_by_id_and_version, store_diff


def insert_rule(cur, rule_hash: str, canonical_rule: dict):
    """
    Insert rule into database with deduplication, versioning, and diff tracking.
    """

    # -----------------------------
    # ✅ Validate required fields
    # -----------------------------
    required_fields = ["type", "action", "conditions"]
    for field in required_fields:
        if field not in canonical_rule:
            raise ValueError(f"Missing required field: {field}")

    # -----------------------------
    # ✅ Generate semantic rule_id
    # -----------------------------
    rule_id = generate_rule_id(canonical_rule)

    # -----------------------------
    # 1️⃣ CHECK DUPLICATE (HASH)
    # -----------------------------
    cur.execute(
        "SELECT id FROM rules WHERE rule_hash = %s",
        (rule_hash,)
    )
    if cur.fetchone():
        print("✓ Duplicate rule skipped")
        return

    # -----------------------------
    # 2️⃣ GET CURRENT VERSION
    # -----------------------------
    cur.execute(
        "SELECT MAX(version) FROM rules WHERE rule_id = %s",
        (rule_id,)
    )
    result = cur.fetchone()[0]
    old_version = result if result else 0
    new_version = old_version + 1

    # -----------------------------
    # 3️⃣ DIFF (ONLY IF v2+)
    # -----------------------------
    diff = None

    if old_version > 0:
        old_rule = get_rule_by_id_and_version(rule_id, old_version)

        # 🔍 Debug (keep temporarily)
        print("\nDEBUG OLD RULE:", old_rule)
        print("DEBUG NEW RULE:", canonical_rule)

        if old_rule:
            diff = diff_rules(old_rule, canonical_rule)

    # -----------------------------
    # 4️⃣ INSERT RULE (WITH CANONICAL)
    # -----------------------------
    cur.execute("""
        INSERT INTO rules (
            rule_hash, rule_id, version, type, title,
            regulator, action, description, canonical_rule
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        rule_hash,
        rule_id,
        new_version,
        canonical_rule.get("type"),
        "",
        "UNKNOWN",
        canonical_rule.get("action"),
        "",
        json.dumps(canonical_rule)  # 🔥 CRITICAL
    ))

    db_rule_id = cur.fetchone()[0]

    # -----------------------------
    # 5️⃣ INSERT CONDITIONS
    # -----------------------------
    for cond in canonical_rule["conditions"]:
        cur.execute("""
            INSERT INTO conditions (rule_id, field, operator, value)
            VALUES (%s,%s,%s,%s)
        """, (
            db_rule_id,
            cond["field"],
            cond["operator"],
            json.dumps(cond["value"])
        ))

    # -----------------------------
    # 6️⃣ STORE DIFF (IF EXISTS)
    # -----------------------------
    if diff:
        store_diff(rule_id, old_version, new_version, diff)

    # -----------------------------
    # 7️⃣ OUTPUT
    # -----------------------------
    print(f"✓ Inserted rule {rule_id} v{new_version}")

    if diff:
        print("\n--- DIFF ---\n", diff)