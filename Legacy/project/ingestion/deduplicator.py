"""
Deduplicator: prevents re-processing of already-ingested URLs/content.
"""

import logging
from typing import Optional

from ingestion.database import get_connection

logger = logging.getLogger(__name__)


def is_url_processed(url: str) -> bool:
    """Check if a URL has already been stored in raw_documents."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM raw_documents WHERE url = %s", (url,))
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    except Exception as e:
        logger.error(f"Dedup check failed for {url}: {e}")
        return False
    finally:
        if conn:
            conn.close()


def is_hash_exists(content_hash: str) -> bool:
    """Check if content with this hash has already been stored."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM raw_documents WHERE content_hash = %s", (content_hash,))
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    except Exception as e:
        logger.error(f"Hash check failed for {content_hash[:12]}: {e}")
        return False
    finally:
        if conn:
            conn.close()


def is_llm_processed(url: str) -> bool:
    """Check if a URL has already been processed through LLM extraction."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM processed_documents WHERE url = %s AND status = 'success'",
            (url,),
        )
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    except Exception as e:
        logger.error(f"Process check failed for {url}: {e}")
        return False
    finally:
        if conn:
            conn.close()
