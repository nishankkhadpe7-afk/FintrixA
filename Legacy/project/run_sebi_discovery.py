#!/usr/bin/env python3
"""
Run SEBI RSS discovery pipeline.
"""

import json
import logging
import sys

from ingestion.sebi_pipeline_orchestrator import run_sebi_discovery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def main():
    print("\n" + "=" * 70)
    print("SEBI RSS DISCOVERY PIPELINE")
    print("=" * 70 + "\n")

    try:
        results = run_sebi_discovery(max_entries=25)
        print(json.dumps(results, indent=2, default=str))
    except KeyboardInterrupt:
        print("\n\n❌ Discovery interrupted by user")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌ Discovery failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
