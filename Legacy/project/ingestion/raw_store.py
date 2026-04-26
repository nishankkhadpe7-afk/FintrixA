"""
Raw Document Store: persists EXACT content from RBI circulars.

No mutation allowed after storage (audit requirement).
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from ingestion.database import get_connection
from ingestion.source_validation import validate_regulator_url

logger = logging.getLogger(__name__)


def compute_content_hash(content: str) -> str:
    """SHA256 hash of content for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def store_raw_document(
    source: str,
    title: str,
    url: str,
    content: str,
    published_date: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Store raw document in database.

    Returns:
        {"id": int, "content_hash": str} on success
        None if duplicate (idempotent)
    """
    if url.startswith(("http://", "https://")):
        validate_regulator_url(url, source=source)

    content_hash = compute_content_hash(content)

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Check if URL already exists (idempotent)
        cur.execute("SELECT id, content_hash FROM raw_documents WHERE url = %s", (url,))
        existing = cur.fetchone()

        if existing:
            logger.info(f"Raw document already exists for {url}")
            cur.close()
            return {"id": existing[0], "content_hash": existing[1]}

        # Check if same content exists under different URL
        cur.execute("SELECT id FROM raw_documents WHERE content_hash = %s", (content_hash,))
        hash_match = cur.fetchone()

        if hash_match:
            logger.info(f"Content hash match found for {url} (same content, different URL)")

        # Insert raw document
        cur.execute(
            """
            INSERT INTO raw_documents (source, title, url, published_date, content, content_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            (source, title, url, published_date, content, content_hash),
        )

        result = cur.fetchone()
        conn.commit()
        cur.close()

        if result:
            doc_id = result[0]
            logger.info(f"Raw document stored: id={doc_id}, hash={content_hash[:12]}...")
            return {"id": doc_id, "content_hash": content_hash}
        else:
            logger.info(f"Raw document insert skipped (conflict) for {url}")
            return None

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to store raw document for {url}: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_raw_document(url: str) -> Optional[Dict[str, Any]]:
    """Retrieve a raw document by URL."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, source, title, url, content, content_hash FROM raw_documents WHERE url = %s",
            (url,),
        )
        row = cur.fetchone()
        cur.close()

        if not row:
            return None

        return {
            "id": row[0],
            "source": row[1],
            "title": row[2],
            "url": row[3],
            "content": row[4],
            "content_hash": row[5],
        }
    finally:
        if conn:
            conn.close()
