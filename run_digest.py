"""Waste news digest.

Examples:
    python run_digest.py                 # default lookback (24h, or 72h on Mondays)
    python run_digest.py --hours 168     # last 7 days
    python run_digest.py --render reports/2026-10-29_0645   # rebuild HTML after adding top_stories.md
"""
import argparse
import sys

from waste_digest.config import load_config
from waste_digest.pipeline import rerender, run


def main() -> int:
    p = argparse.ArgumentParser(description="Build the waste industry news digest.")
    p.add_argument("--hours", type=int, help="lookback window in hours (e.g. 24, 72, 168)")
    p.add_argument("--days", type=int, help="lookback window in days (alternative to --hours)")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--no-history", action="store_true", help="don't mark stories as seen (test runs)")
    p.add_argument("--sources", nargs="*", help="only run these sources (e.g. trade_feeds sec_edgar)")
    p.add_argument("--render", metavar="REPORT_DIR", help="re-render an existing report's HTML and exit")
    args = p.parse_args()

    if args.render:
        print(rerender(args.render))
        return 0
    hours = args.hours or (args.days * 24 if args.days else None)
    run(load_config(args.config), hours=hours, update_history=not args.no_history, only_sources=args.sources)
    return 0


if __name__ == "__main__":
    sys.exit(main())
