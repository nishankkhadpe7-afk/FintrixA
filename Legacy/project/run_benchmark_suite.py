#!/usr/bin/env python3
"""
Run benchmark scenarios against the local rule engine and compare expected vs actual results.

Usage:
    python run_benchmark_suite.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from api.services.simulation_service import simulate
from utils.rule_identity import generate_rule_id


ROOT = Path(__file__).resolve().parent
RULE_DATA_PATH = ROOT / "seed_data" / "rule_seed_data.json"
BENCHMARK_DATA_PATH = ROOT / "seed_data" / "benchmark_scenarios.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_rule_key_map() -> Dict[str, str]:
    payload = load_json(RULE_DATA_PATH)
    mapping: Dict[str, str] = {}
    for item in payload.get("rules", []):
        mapping[item["key"]] = generate_rule_id(item["rule"])
    return mapping


def determine_result(actions: List[str]) -> str:
    normalized = [action.upper() for action in actions]
    if "DENY" in normalized:
        return "DENY"
    if "FLAG" in normalized:
        return "FLAG"
    return "ALLOW"


def run_suite() -> dict:
    benchmarks = load_json(BENCHMARK_DATA_PATH).get("benchmarks", [])
    rule_key_map = build_rule_key_map()
    results = []
    passed = 0

    for benchmark in benchmarks:
        simulation = simulate([benchmark["input"]], debug=True)
        simulation_result = simulation["results"][0]
        matched_rules = simulation_result.get("matched_rules", [])
        actual_rule_ids = [rule["rule_id"] for rule in matched_rules]
        actual_actions = [rule["action"] for rule in matched_rules]
        actual_result = determine_result(actual_actions)

        expected_rule_ids = [rule_key_map[key] for key in benchmark.get("expected_rule_keys", [])]
        result_match = actual_result == benchmark["expected_result"]
        rule_match = sorted(actual_rule_ids) == sorted(expected_rule_ids)
        ok = result_match and rule_match

        if ok:
            passed += 1

        results.append(
            {
                "id": benchmark["id"],
                "title": benchmark["title"],
                "domain": benchmark["domain"],
                "expected_result": benchmark["expected_result"],
                "actual_result": actual_result,
                "expected_rule_ids": expected_rule_ids,
                "actual_rule_ids": actual_rule_ids,
                "passed": ok,
            }
        )

    return {
        "total": len(benchmarks),
        "passed": passed,
        "failed": len(benchmarks) - passed,
        "results": results,
    }


def main() -> None:
    report = run_suite()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
