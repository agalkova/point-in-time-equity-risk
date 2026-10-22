from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from risk_managed_momentum.data.membership import (
    WIKIPEDIA_SP500_URL,
    WIKIPEDIA_SP500_HISTORY_URL,
    daily_membership,
    fetch_wikipedia_membership,
    symbols_needed_for_period,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build point-in-time S&P 500 membership")
    parser.add_argument("--start", default="2019-06-01")
    parser.add_argument("--end", default="2026-09-30")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = fetch_wikipedia_membership()
    membership = daily_membership(source, start=args.start, end=args.end)
    symbols = symbols_needed_for_period(source, start=args.start)

    output_dir = PROJECT_ROOT / "data" / "interim" / "membership"
    output_dir.mkdir(parents=True, exist_ok=True)
    membership.to_csv(output_dir / "sp500_daily_membership.csv.gz", index=False, compression="gzip")
    source.current.to_csv(output_dir / "sp500_current_components.csv", index=False)
    source.changes.to_csv(output_dir / "sp500_changes.csv", index=False)
    (output_dir / "sp500_symbols.txt").write_text("\n".join(symbols) + "\n")

    manifest = {
        "source_urls": [WIKIPEDIA_SP500_URL, WIKIPEDIA_SP500_HISTORY_URL],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "start": args.start,
        "end": args.end,
        "current_constituents": int(source.current["ticker"].nunique()),
        "change_rows": int(len(source.changes)),
        "requested_symbols": len(symbols),
        "membership_rows": int(len(membership)),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
