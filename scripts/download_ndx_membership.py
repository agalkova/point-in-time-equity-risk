from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from risk_managed_momentum.data.ndx import (
    download_ndx_snapshots,
    expand_monthly_membership,
    month_end_snapshot_dates,
    normalize_ndx_snapshots,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_7_ndx.toml").open("rb") as handle:
        config = tomllib.load(handle)
    universe = config["universe"]
    dates = month_end_snapshot_dates(universe["snapshot_start"], universe["evaluation_end"])
    raw_dir = PROJECT_ROOT / "data/raw/ptdata/ndx_membership"
    paths = download_ndx_snapshots(dates, raw_dir)
    payloads = [json.loads(path.read_text()) for path in paths]
    nonempty_payloads = [payload for payload in payloads if payload.get("constituents")]
    snapshots = normalize_ndx_snapshots(paths)
    daily = expand_monthly_membership(
        snapshots,
        start=universe["snapshot_start"],
        end=universe["evaluation_end"],
    )
    output_dir = PROJECT_ROOT / "data/interim/ndx"
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshots.to_csv(
        output_dir / "ndx_membership_snapshots.csv.gz", index=False, compression="gzip"
    )
    daily.to_csv(output_dir / "ndx_daily_membership.csv.gz", index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "provider": "ptdata",
        "endpoint": "https://api.ptdata.io/v1/index-constituents",
        "index": "NDX",
        "snapshot_frequency": "calendar month end",
        "requested_snapshots": len(dates),
        "nonempty_snapshots": int(snapshots["snapshot_date"].nunique()),
        "empty_snapshots": len(payloads) - len(nonempty_payloads),
        "first_nonempty_snapshot": str(snapshots["snapshot_date"].min().date()),
        "last_nonempty_snapshot": str(snapshots["snapshot_date"].max().date()),
        "unique_tickers": int(snapshots["ticker"].nunique()),
        "daily_membership_rows": len(daily),
        "limitation": (
            "Month-end snapshots delay within-month membership changes. The free provider "
            "returned empty constituent lists before the first_nonempty_snapshot."
        ),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
