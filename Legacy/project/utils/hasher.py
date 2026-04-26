import hashlib
import json


def generate_rule_hash(canonical_rule):
    # Convert to stable JSON string
    rule_str = json.dumps(canonical_rule, sort_keys=True)

    # SHA256 hash
    return hashlib.sha256(rule_str.encode()).hexdigest()