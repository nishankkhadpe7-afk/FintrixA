#!/usr/bin/env python3
"""
Batch-ingest reviewed SEBI documents listed in documents/sebi/manifest.json.

Only files that actually exist on disk will be ingested.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingestion.manual_document_ingestion import ingest_local_document


PROJECT_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = PROJECT_ROOT / "documents" / "sebi" / "manifest.json"


def load_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-ingest reviewed SEBI documents from the manifest."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess documents even if they were previously marked successful.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = load_manifest()
    documents = manifest.get("documents", [])

    summary = {
      "processed": 0,
      "ingested": 0,
      "skipped_missing_file": 0,
      "failed": 0,
      "results": []
    }

    for item in documents:
        suggested_file = item.get("suggested_file")
        if not suggested_file:
            continue

        file_path = (PROJECT_ROOT / suggested_file).resolve()
        if not file_path.exists():
            summary["skipped_missing_file"] += 1
            summary["results"].append({
                "id": item.get("id"),
                "title": item.get("title"),
                "status": "missing_file",
                "file_path": str(file_path),
            })
            continue

        summary["processed"] += 1
        try:
            result = ingest_local_document(
                file_path=str(file_path),
                title=item["title"],
                source="SEBI",
                official_url=item.get("official_url"),
                published_date=item.get("published_date"),
                force=args.force,
            )
            if result.get("status") in {"success", "skipped"}:
                summary["ingested"] += 1
            summary["results"].append({
                "id": item.get("id"),
                "title": item.get("title"),
                "status": result.get("status"),
                "forced": result.get("forced", args.force),
                "total_extracted": result.get("total_extracted", 0),
                "detail": result.get("detail"),
            })
        except Exception as exc:
            summary["failed"] += 1
            summary["results"].append({
                "id": item.get("id"),
                "title": item.get("title"),
                "status": "failed",
                "forced": args.force,
                "detail": str(exc),
            })

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
