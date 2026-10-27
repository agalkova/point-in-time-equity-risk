from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.sec_identity import (
    attach_interval_names,
    build_sec_identity_map,
    load_fsds_submission_registry,
    load_sec_ticker_registry,
    membership_intervals,
    resolve_identity_names,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build point-in-time ticker-to-CIK identity intervals."
    )
    parser.add_argument(
        "--fsds-archive",
        type=Path,
        help="Optional official SEC FSDS quarterly ZIP used for decisive filing-name matches.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    membership_dir = PROJECT_ROOT / "data/interim/membership"
    current = pd.read_csv(membership_dir / "sp500_v12_current_components.csv")
    changes = pd.read_csv(membership_dir / "sp500_v12_changes.csv")
    daily = pd.read_csv(membership_dir / "sp500_v12_daily_membership.csv.gz", parse_dates=["date"])
    registry_path = PROJECT_ROOT / "data/raw/sec/company_tickers.json"
    if not registry_path.is_file():
        raise FileNotFoundError(
            "Download the official SEC company_tickers.json file before building identities"
        )
    intervals = attach_interval_names(membership_intervals(daily), current, changes)
    identities = build_sec_identity_map(intervals, current, load_sec_ticker_registry(registry_path))
    identity_sources = ["SEC company_tickers.json", "point-in-time S&P 500 membership"]
    if args.fsds_archive:
        identities = resolve_identity_names(
            identities, load_fsds_submission_registry(args.fsds_archive)
        )
        identity_sources.append(f"SEC FSDS submission names ({args.fsds_archive.name})")
    output_dir = PROJECT_ROOT / "data/interim/sec_identity"
    output_dir.mkdir(parents=True, exist_ok=True)
    identities.to_csv(output_dir / "sp500_sec_identity_intervals.csv", index=False)
    identities[identities["status"].ne("RESOLVED")].to_csv(
        output_dir / "sp500_sec_identity_review_queue.csv", index=False
    )
    resolved = identities["status"].eq("RESOLVED")
    interval_coverage = float(resolved.mean())
    membership_day_coverage = float(
        identities.loc[resolved, "membership_days"].sum() / identities["membership_days"].sum()
    )
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source": " and ".join(identity_sources),
        "fsds_archive": str(args.fsds_archive) if args.fsds_archive else None,
        "intervals": len(identities),
        "unique_tickers": int(identities["ticker"].nunique()),
        "resolved_intervals": int(resolved.sum()),
        "review_intervals": int((~resolved).sum()),
        "interval_coverage": interval_coverage,
        "membership_day_coverage": membership_day_coverage,
        "bulk_download_gate": {
            "minimum_membership_day_coverage": 0.90,
            "passes": bool(membership_day_coverage >= 0.90),
        },
        "model_enablement_gate": {
            "minimum_interval_coverage": 0.95,
            "passes": bool(interval_coverage >= 0.95),
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
