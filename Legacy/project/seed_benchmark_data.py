#!/usr/bin/env python3
"""
Load benchmark-friendly seed rules into the local RegTech database.

Usage:
    python seed_benchmark_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from db import get_connection
from insert_rule import insert_rule
from utils.hasher import generate_rule_hash
from utils.rule_identity import generate_rule_id


ROOT = Path(__file__).resolve().parent
RULE_DATA_PATH = ROOT / "seed_data" / "rule_seed_data.json"


def load_rule_seed_data() -> dict:
    with RULE_DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    payload = load_rule_seed_data()
    rules = payload.get("rules", [])

    if not rules:
        print("No seed rules found.")
        return

    conn = get_connection()
    summary = {"inserted_or_updated": 0, "processed": len(rules)}
    rule_key_map = {}

    try:
        for item in rules:
            canonical_rule = item["rule"]
            rule_hash = generate_rule_hash(canonical_rule)
            rule_id = generate_rule_id(canonical_rule)
            rule_key_map[item["key"]] = {
                "rule_id": rule_id,
                "domain": item.get("domain", "unknown"),
                "description": item.get("description", ""),
                "action": canonical_rule["action"],
            }

            cur = conn.cursor()
            try:
                insert_rule(cur, rule_hash, canonical_rule)
                conn.commit()
                summary["inserted_or_updated"] += 1
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    finally:
        conn.close()

    print("\nSeed load complete")
    print(json.dumps(summary, indent=2))
    print("\nRule key map:")
    print(json.dumps(rule_key_map, indent=2))


if __name__ == "__main__":
    main()
