"""
SEBI RSS discovery pipeline.

This keeps SEBI as a first-class ingestion source by syncing official RSS items
into a reviewed intake file for manual download and ingestion.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from ingestion.deduplicator import is_url_processed
from ingestion.rss_fetcher import fetch_rss
from ingestion.source_validation import validate_regulator_url

logger = logging.getLogger(__name__)

SEBI_RSS_URL = "https://www.sebi.gov.in/sebirss.xml"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTAKE_PATH = PROJECT_ROOT / "documents" / "sebi" / "rss_intake.json"


def run_sebi_discovery(max_entries: int = 25) -> Dict[str, Any]:
    entries = fetch_rss(url=SEBI_RSS_URL)
    if not entries:
        return {"status": "success", "total_seen": 0, "new_items": 0, "items": []}

    intake = _load_intake()
    known_urls = {item["official_url"] for item in intake.get("documents", []) if item.get("official_url")}

    discovered = []
    for entry in entries[:max_entries]:
        try:
            official_url = validate_regulator_url(entry["link"], source="SEBI")
        except ValueError:
            continue

        if official_url in known_urls or is_url_processed(official_url):
            continue

        item = {
            "id": f"sebi-rss-{len(intake.get('documents', [])) + len(discovered) + 1:03d}",
            "category": _infer_category(official_url),
            "title": entry["title"],
            "official_url": official_url,
            "suggested_file": _suggested_file_path(entry["title"], official_url, entry.get("published")),
            "published_date": entry.get("published"),
            "priority": "medium",
            "status": "pending_review",
            "source": "SEBI RSS",
        }
        discovered.append(item)

    if discovered:
        intake.setdefault("documents", []).extend(discovered)
        INTAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
        INTAKE_PATH.write_text(json.dumps(intake, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "total_seen": len(entries),
        "new_items": len(discovered),
        "items": discovered,
        "intake_file": str(INTAKE_PATH),
    }


def _load_intake() -> Dict[str, Any]:
    if not INTAKE_PATH.exists():
        return {"documents": []}
    return json.loads(INTAKE_PATH.read_text(encoding="utf-8"))


def _infer_category(url: str) -> str:
    path = urlparse(url).path.lower()
    if "master-circular" in path:
        return "master_circulars"
    if "regulation" in path:
        return "regulations"
    return "circulars"


def _slugify(text: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in text)
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")[:80]


def _suggested_file_path(title: str, url: str, published_date: str | None) -> str:
    category = _infer_category(url)
    date_prefix = (published_date or "undated").replace(":", "-").replace("/", "-")
    if "T" in date_prefix:
        date_prefix = date_prefix.split("T", 1)[0]
    slug = _slugify(title) or "sebi_document"
    return f"documents/sebi/{category}/{date_prefix}_{slug}.pdf"
