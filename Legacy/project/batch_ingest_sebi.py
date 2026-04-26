#!/usr/bin/env python3
"""
Batch ingest all SEBI PDFs from documents/sebi/.

Usage:
    python batch_ingest_sebi.py
"""

import json
import logging
from pathlib import Path
from ingestion.manual_document_ingestion import ingest_local_document
from ingestion.database import init_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

SEBI_ROOT = Path(__file__).parent / "documents" / "sebi"

# Map PDF filenames to titles using manifest
def load_manifest():
    manifest_path = SEBI_ROOT / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
        return {doc["id"]: doc for doc in data.get("documents", [])}
    return {}


def find_all_pdfs():
    """Find all PDFs recursively under documents/sebi/."""
    return sorted(SEBI_ROOT.rglob("*.pdf"))


def main():
    init_schema()

    pdfs = find_all_pdfs()
    if not pdfs:
        print("❌ No PDFs found in documents/sebi/")
        return

    print(f"\n{'='*60}")
    print(f"SEBI BATCH INGESTION: {len(pdfs)} PDFs found")
    print(f"{'='*60}\n")

    results = {"success": 0, "skipped": 0, "failed": 0}

    for idx, pdf_path in enumerate(pdfs, 1):
        # Build relative path from project root
        rel_path = pdf_path.relative_to(Path(__file__).parent)
        category = pdf_path.parent.name  # circulars, master_circulars, regulations
        title = f"SEBI {category.replace('_', ' ').title()} - {pdf_path.stem}"

        print(f"[{idx}/{len(pdfs)}] Ingesting: {rel_path}")
        print(f"   Title: {title}")

        try:
            result = ingest_local_document(
                file_path=str(rel_path),
                title=title,
                source="SEBI",
            )

            status = result.get("status", "unknown")
            rules_count = result.get("total_extracted", 0)

            if status == "success":
                results["success"] += 1
                print(f"   ✅ Success — {rules_count} rules extracted")
            elif status == "skipped":
                results["skipped"] += 1
                print(f"   ⏭️  Skipped — {result.get('detail', 'already processed')}")
            else:
                results["failed"] += 1
                print(f"   ❌ Failed — {result.get('detail', 'unknown error')}")

        except Exception as e:
            results["failed"] += 1
            print(f"   ❌ Error — {e}")

        print()

    # Summary
    print(f"{'='*60}")
    print(f"BATCH INGESTION COMPLETE")
    print(f"  ✅ Success: {results['success']}")
    print(f"  ⏭️  Skipped: {results['skipped']}")
    print(f"  ❌ Failed:  {results['failed']}")
    print(f"  📊 Total:   {len(pdfs)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
