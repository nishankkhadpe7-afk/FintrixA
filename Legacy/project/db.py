import json
from database_pool import get_connection as get_pooled_connection


# ---------------------------
# CONNECTION
# ---------------------------
def get_connection():
    return get_pooled_connection()

def execute_query(query, params=None, fetch=False):
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(query, params)

    result = None
    if fetch:
        result = cur.fetchall()

    cur.close()
    conn.close()

    return result


# ---------------------------
# INSERT RULE
# ---------------------------
def insert_rule(rule_id, rule_hash, version, rule_type, action, canonical_rule):
    query = """
    INSERT INTO rules (rule_id, rule_hash, version, type, action, canonical_rule)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    execute_query(query, (
        rule_id,
        rule_hash,
        version,
        rule_type,
        action,
        json.dumps(canonical_rule)
    ))


# ---------------------------
# GET RULE (FOR DIFF ENGINE)
# ---------------------------
def get_rule_by_id_and_version(rule_id, version):
    query = """
    SELECT canonical_rule
    FROM rules
    WHERE rule_id = %s AND version = %s
    """

    result = execute_query(query, (rule_id, version), fetch=True)

    if not result:
        return None

    data = result[0][0]

    if data is None:
        return None

    # 🔥 Handle both JSONB return types
    if isinstance(data, dict):
        return data
    else:
        return json.loads(data)


# ---------------------------
# CHECK EXISTING RULE
# ---------------------------
def get_rule_by_hash(rule_hash):
    query = """
    SELECT rule_id, version
    FROM rules
    WHERE rule_hash = %s
    """
    result = execute_query(query, (rule_hash,), fetch=True)

    if not result:
        return None

    return result[0]


def get_latest_version(rule_id):
    query = """
    SELECT MAX(version)
    FROM rules
    WHERE rule_id = %s
    """
    result = execute_query(query, (rule_id,), fetch=True)

    if not result or result[0][0] is None:
        return 0

    return result[0][0]


# ---------------------------
# STORE DIFF
# ---------------------------
def store_diff(rule_id, v1, v2, diff):
    query = """
    INSERT INTO rule_changes (rule_id, version_from, version_to, diff)
    VALUES (%s, %s, %s, %s)
    """
    execute_query(query, (
        rule_id,
        v1,
        v2,
        json.dumps(diff)
    ))
