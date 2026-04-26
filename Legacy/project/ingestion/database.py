"""
Database connection and schema setup for ingestion module.
"""

import os
import logging

logger = logging.getLogger(__name__)

from database_pool import get_connection


def init_schema():
    """
    Create ingestion tables if they don't exist.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(schema_sql)
        cur.execute(
            """
            ALTER TABLE rules
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
            """
        )
        conn.commit()
        cur.close()
        logger.info("Ingestion schema initialized")
    except Exception as e:
        logger.error(f"Schema init failed: {e}")
        raise
    finally:
        if conn:
            conn.close()
