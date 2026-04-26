#!/usr/bin/env python3
"""
Ingest a reviewed local SEBI document into the existing extraction pipeline.

Usage:
    python ingest_sebi_document.py "documents/sebi/sample_sebi_note.txt" "Sample SEBI Circular"
"""

from __future__ import annotations

import argparse
import json

from ingestion.manual_document_ingestion import ingest_local_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a reviewed local SEBI document into the extraction pipeline."
    )
    parser.add_argument("file_path", help="Local path to the reviewed SEBI document")
    parser.add_argument("title", help="Display title for the document")
    parser.add_argument(
        "official_url",
        nargs="?",
        default=None,
        help="Official SEBI source URL for the document",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess the document even if it was already marked successful.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = ingest_local_document(
        file_path=args.file_path,
        title=args.title,
        source="SEBI",
        official_url=args.official_url,
        force=args.force,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
