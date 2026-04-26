#!/usr/bin/env python3
"""
Run RBI Circular Ingestion Pipeline

Usage:
    python run_ingestion.py
"""

import json
import logging
import sys

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

from ingestion.pipeline_orchestrator import run_pipeline


def main():
    print("\n" + "=" * 70)
    print("RBI CIRCULAR INGESTION PIPELINE")
    print("=" * 70 + "\n")

    try:
        results = run_pipeline(max_entries=10)

        print("\n" + "=" * 70)
        print("OUTPUT")
        print("=" * 70)

        if results:
            print(json.dumps(results, indent=2, default=str))

            print(f"\n✅ {len(results)} circulars processed successfully")
            total_rules = sum(len(r.get("rules", [])) for r in results)
            print(f"📋 {total_rules} total rules extracted")
        else:
            print("\nNo new rules extracted (all circulars already processed or no new entries)")

        print("\n" + "=" * 70)

    except KeyboardInterrupt:
        print("\n\n❌ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
