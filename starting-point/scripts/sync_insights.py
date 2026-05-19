"""Sync accumulated insights back to wiki pages and HINTS dictionary.

Run periodically (weekly/monthly) to enrich the knowledge base with
user-verified data from actual conversations.

Usage:
    python sync_insights.py --dry-run    # Preview changes
    python sync_insights.py              # Apply changes
    python sync_insights.py --hints-only # Only update HINTS, skip wiki
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from starting_point.wiki import sync_all_insights


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync insights to wiki + HINTS")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--hints-only", action="store_true", help="Only sync HINTS, skip wiki pricing")
    args = parser.parse_args()

    print(f"Insights sync {'(dry run)' if args.dry_run else '(LIVE)'}")
    print("=" * 40)

    result = sync_all_insights(dry_run=args.dry_run)

    hints = result["hints"]
    pricing = result["pricing"]

    print(f"\nHINTS updates:")
    for h in hints["added"]:
        print(f"  + {h}")
    for h in hints["skipped"]:
        print(f"  ~ {h}")

    if not args.hints_only:
        print(f"\nPricing updates:")
        for p in pricing["updated"]:
            print(f"  + {p}")
        for p in pricing["skipped"]:
            print(f"  ~ {p}")

    total_added = len(hints["added"]) + len(pricing.get("updated", []))
    print(f"\nTotal changes: {total_added}")


if __name__ == "__main__":
    main()
