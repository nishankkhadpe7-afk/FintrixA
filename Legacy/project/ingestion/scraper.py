"""
Web Scraper for RBI circular pages.

Extracts title, date, and full textual content from circular HTML pages.
"""

import logging
import time
from typing import Any, Dict, Optional

import httpx
from bs4 import BeautifulSoup
from ingestion.source_validation import validate_regulator_url

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds (exponential: 2, 4, 8)
TIMEOUT = 30


def scrape_circular(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch and parse an RBI circular page.

    Returns:
        {
            "title": str,
            "date": str | None,
            "content": str,
            "url": str
        }
        or None on failure.
    """
    try:
        validated_url = validate_regulator_url(url, source="RBI")
    except ValueError as exc:
        logger.error(f"Rejected non-official scrape URL: {exc} [{url}]")
        return None

    html = _fetch_with_retry(validated_url)

    if not html:
        return None

    try:
        return _parse_circular(html, validated_url)
    except Exception as e:
        logger.error(f"Parse failed for {url}: {e}")
        return None


def _fetch_with_retry(url: str) -> Optional[str]:
    """Fetch URL with exponential backoff retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.get(
                url,
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (RegTech Bot; compliance audit)"
                },
            )
            response.raise_for_status()
            return response.text

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} for {url} (attempt {attempt}/{MAX_RETRIES})")
        except httpx.RequestError as e:
            logger.warning(f"Request failed for {url} (attempt {attempt}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF ** attempt
            logger.info(f"Retrying in {wait}s...")
            time.sleep(wait)

    logger.error(f"All {MAX_RETRIES} attempts failed for {url}")
    return None


def _parse_circular(html: str, url: str) -> Dict[str, Any]:
    """
    Parse RBI circular HTML into structured data.
    Extracts title, date, and full text content.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Title: try multiple selectors (RBI pages vary)
    title = _extract_title(soup)

    # Date: try common patterns
    date = _extract_date(soup)

    # Content: extract full text
    content = _extract_content(soup)

    if not content or len(content.strip()) < 50:
        logger.warning(f"Insufficient content extracted from {url} ({len(content)} chars)")

    return {
        "title": title,
        "date": date,
        "content": content.strip(),
        "url": url,
    }


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract circular title from page."""
    # Try specific RBI selectors
    for selector in [
        "h1",
        ".page-title",
        "#content h2",
        "title",
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get_text(strip=True):
            return tag.get_text(strip=True)

    return "Untitled Circular"


def _extract_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract publication date from page."""
    # Look for common date patterns in RBI pages
    for selector in [
        ".date",
        ".circular-date",
        "time",
    ]:
        tag = soup.select_one(selector)
        if tag:
            return tag.get_text(strip=True)

    # Search text for date-like patterns
    import re
    text = soup.get_text()
    date_match = re.search(
        r"(?:dated?\s*:?\s*)(\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        text,
        re.IGNORECASE,
    )
    if date_match:
        return date_match.group(1).strip()

    return None


def _extract_content(soup: BeautifulSoup) -> str:
    """
    Extract full textual content from circular.
    Handles paragraphs, lists, and tables.
    """
    # Try main content area first
    content_area = None
    for selector in [
        "#content",
        ".main-content",
        "main",
        "article",
        ".rbi-content",
        "body",
    ]:
        content_area = soup.select_one(selector)
        if content_area:
            break

    if not content_area:
        content_area = soup

    parts = []

    for element in content_area.find_all(
        ["p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "div"]
    ):
        text = element.get_text(separator=" ", strip=True)
        if text and len(text) > 2:
            parts.append(text)

    # Deduplicate consecutive identical lines
    deduped = []
    for part in parts:
        if not deduped or part != deduped[-1]:
            deduped.append(part)

    return "\n".join(deduped)
