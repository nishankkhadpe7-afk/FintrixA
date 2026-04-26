"""
Engine package: Multi-rule execution and database integration.
"""

from engine.executor import (
    evaluate_condition,
    evaluate_node,
    evaluate_rule,
    fetch_active_rules,
    evaluate_all_rules,
    execute_against_db,
    execute_batch,
    aggregate_actions
)

__all__ = [
    "evaluate_condition",
    "evaluate_node",
    "evaluate_rule",
    "fetch_active_rules",
    "evaluate_all_rules",
    "execute_against_db",
    "execute_batch",
    "aggregate_actions"
]
