#!/usr/bin/env python3
"""Ingest reviewed SEBI master circulars / circulars into the active backend.

Default source: Legacy/project/documents/sebi/manifest.json

Examples:
    python scripts/ingest_sebi_documents.py
    python scripts/ingest_sebi_documents.py --dry-run
    python scripts/ingest_sebi_documents.py --mock (generates synthetic rules for testing without LLM)
    python scripts/ingest_sebi_documents.py --manifest ..\\Legacy\\project\\documents\\sebi\\manifest.json --doc-root ..\\Legacy\\project
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.rules.sebi_ingest import ingest_sebi_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest reviewed SEBI documents into ComplianceRule rows.")
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT.parents[1] / "Legacy" / "project" / "documents" / "sebi" / "manifest.json"),
        help="Path to the SEBI manifest.json file.",
    )
    parser.add_argument(
        "--doc-root",
        default=str(PROJECT_ROOT.parents[1] / "Legacy" / "project"),
        help="Root directory that contains the document paths from the manifest.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on the number of manifest entries to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and validate rules without persisting them.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Generate synthetic SEBI rules from PDF text patterns (no LLM key required, for testing).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = ingest_sebi_manifest(
        manifest_path=Path(args.manifest),
        doc_root=Path(args.doc_root),
        limit=args.limit,
        dry_run=args.dry_run,
        use_mock=args.mock,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
