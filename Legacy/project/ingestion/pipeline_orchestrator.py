"""
Pipeline Orchestrator: end-to-end RBI circular ingestion.

Flow: RSS → Dedup → Scrape → Store Raw → LLM Extract → Output JSON
"""

import json
import logging
from typing import Any, Dict, List

from ingestion.rss_fetcher import fetch_rss
from ingestion.deduplicator import is_url_processed, is_llm_processed
from ingestion.scraper import scrape_circular
from ingestion.raw_store import store_raw_document
from ingestion.llm_extractor import extract_rules_from_content
from ingestion.database import get_connection, init_schema
from ingestion.rule_persistence import persist_extracted_rules
from ingestion.source_validation import validate_regulator_url

logger = logging.getLogger(__name__)


def run_pipeline(max_entries: int = 50) -> List[Dict[str, Any]]:
    """
    Execute the full ingestion pipeline.

    1. Fetch RSS feed
    2. Filter out already-processed URLs
    3. Scrape each new circular
    4. Store raw content (immutable)
    5. Extract rules via LLM
    6. Record processing status
    7. Return structured output

    Args:
        max_entries: Maximum number of new entries to process per run

    Returns:
        List of {source, url, rules} dicts ready for downstream pipeline
    """
    logger.info("=" * 60)
    logger.info("INGESTION PIPELINE STARTED")
    logger.info("=" * 60)

    # Ensure tables exist
    init_schema()

    # Step 1: Fetch RSS
    entries = fetch_rss()
    if not entries:
        logger.warning("No RSS entries found")
        return []

    # Step 2: Filter new entries
    new_entries = []
    for entry in entries:
        try:
            url = validate_regulator_url(entry["link"], source="RBI")
        except ValueError as exc:
            logger.warning(f"Skipping unsupported entry URL: {exc} [{entry['link']}]")
            continue

        entry["link"] = url
        if is_url_processed(url):
            logger.debug(f"SKIP (already stored): {url}")
            continue
        new_entries.append(entry)

    if not new_entries:
        logger.info("No new circulars to process")
        return []

    # Cap processing
    new_entries = new_entries[:max_entries]
    logger.info(f"Processing {len(new_entries)} new circulars")

    # Step 3–6: Process each entry
    results = []
    stats = {"scraped": 0, "stored": 0, "extracted": 0, "failed": 0}

    for idx, entry in enumerate(new_entries, start=1):
        url = entry["link"]
        title = entry["title"]

        logger.info(f"[{idx}/{len(new_entries)}] Processing: {title[:60]}...")

        try:
            result = _process_entry(entry)
            if result:
                results.append(result)
                stats["extracted"] += 1
            else:
                stats["failed"] += 1

        except Exception as e:
            logger.error(f"[{idx}] Pipeline failed for {url}: {e}")
            stats["failed"] += 1
            _record_failure(url, str(e))
            continue

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION PIPELINE COMPLETE")
    logger.info(f"  Processed: {len(new_entries)}")
    logger.info(f"  Extracted: {stats['extracted']}")
    logger.info(f"  Failed:    {stats['failed']}")
    logger.info("=" * 60)

    return results


def _process_entry(entry: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Process a single RSS entry through the full pipeline.
    """
    url = entry["link"]
    title = entry["title"]
    published = entry.get("published")

    # Step 3: Scrape
    scraped = scrape_circular(url)
    if not scraped or not scraped.get("content"):
        logger.warning(f"Scraping failed or empty for {url}")
        _record_failure(url, "Scraping failed or empty content")
        return None

    # Use scraped title if RSS title is empty
    if not title and scraped.get("title"):
        title = scraped["title"]

    content = scraped["content"]

    # Step 4: Store raw (immutable)
    raw_doc = store_raw_document(
        source="RBI",
        title=title,
        url=url,
        content=content,
        published_date=published,
    )

    if not raw_doc:
        logger.warning(f"Raw storage failed for {url}")
        return None

    # Step 5: LLM extraction (skip if already processed)
    if is_llm_processed(url):
        logger.info(f"LLM already processed: {url}")
        return None

    rules = extract_rules_from_content(content, url=url)
    persistence = persist_extracted_rules(rules or [], source="RBI")

    # Step 6: Record processing status
    status = "success" if rules else "failed"
    error_msg = None if rules else "No rules extracted"
    _record_processing(url, raw_doc["id"], status, rules, error_msg)

    if not rules:
        logger.warning(f"No rules extracted from {url}")
        return None

    # Output contract
    return {
        "source": "RBI",
        "url": url,
        "title": title,
        "rules": rules,
        "stored_rules": persistence.get("rules", []),
        "total_stored": persistence.get("total_stored", 0),
        "total_skipped": persistence.get("total_skipped", 0),
    }


def _record_processing(
    url: str,
    raw_document_id: int,
    status: str,
    result: Any = None,
    error: str = None,
):
    """Record LLM processing result in processed_documents table."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO processed_documents (raw_document_id, url, status, result, error)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE SET
                status = EXCLUDED.status,
                result = EXCLUDED.result,
                error = EXCLUDED.error,
                processed_at = NOW()
            """,
            (
                raw_document_id,
                url,
                status,
                json.dumps(result) if result else None,
                error,
            ),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"Failed to record processing for {url}: {e}")
    finally:
        if conn:
            conn.close()


def _record_failure(url: str, error: str):
    """Record a pipeline failure."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO processed_documents (url, status, error)
            VALUES (%s, 'failed', %s)
            ON CONFLICT (url) DO UPDATE SET
                status = 'failed',
                error = EXCLUDED.error,
                processed_at = NOW()
            """,
            (url, error),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"Failed to record failure for {url}: {e}")
    finally:
        if conn:
            conn.close()
