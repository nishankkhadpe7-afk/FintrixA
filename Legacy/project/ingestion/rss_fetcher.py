"""
RSS Feed Fetcher for RBI circulars.

Polls the RBI notifications RSS feed and returns structured entries.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import feedparser
from ingestion.source_validation import validate_regulator_url

logger = logging.getLogger(__name__)

RBI_RSS_URL = "https://www.rbi.org.in/notifications_rss.xml"


def fetch_rss(url: str = RBI_RSS_URL) -> List[Dict[str, Any]]:
    """
    Fetch and parse the RBI RSS feed.

    Returns:
        List of entries with title, link, published date.
    """
    logger.info(f"Fetching RSS feed: {url}")

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logger.error(f"RSS fetch failed: {e}")
        return []

    if feed.bozo and not feed.entries:
        logger.error(f"RSS parse error: {feed.bozo_exception}")
        return []

    entries = []

    for entry in feed.entries:
        try:
            parsed = {
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", "").strip(),
                "published": _parse_date(entry.get("published")),
            }

            if not parsed["link"]:
                logger.warning(f"Skipping entry with no link: {parsed['title']}")
                continue

            try:
                parsed["link"] = validate_regulator_url(parsed["link"], source="RBI")
            except ValueError as exc:
                logger.warning(f"Skipping non-official RSS entry: {exc} [{parsed['link']}]")
                continue

            entries.append(parsed)

        except Exception as e:
            logger.warning(f"Skipping malformed RSS entry: {e}")
            continue

    logger.info(f"RSS: {len(entries)} entries fetched")
    return entries


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse RSS date string to ISO format. Returns None if unparseable."""
    if not date_str:
        return None

    try:
        # feedparser normalizes dates into time.struct_time via published_parsed
        # but we get the raw string here, try common formats
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except ValueError:
                continue

        return date_str.strip()
    except Exception:
        return None
