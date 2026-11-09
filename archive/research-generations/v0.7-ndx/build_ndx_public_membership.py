from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from risk_managed_momentum.data.ndx import (
    expand_monthly_membership,
    normalize_sparse_component_history,
    verify_sha256,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def comparison(public: pd.DataFrame, ptdata: pd.DataFrame) -> pd.DataFrame:
    public_dates = pd.DatetimeIndex(sorted(public["snapshot_date"].unique()))
    public_rosters = {
        date: set(group["ticker"])
        for date, group in public.groupby("snapshot_date")
    }
    rows = []
    for date, group in ptdata.groupby("snapshot_date"):
        eligible = public_dates[public_dates <= date]
        if eligible.empty:
            continue
        source_date = eligible[-1]
        left = public_rosters[source_date]
        right = set(group["ticker"])
        rows.append(
            {
                "date": date,
                "public_source_date": source_date,
                "public_members": len(left),
                "ptdata_members": len(right),
                "intersection": len(left & right),
                "jaccard": len(left & right) / len(left | right),
                "only_public": ",".join(sorted(left - right)),
                "only_ptdata": ",".join(sorted(right - left)),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_7_ndx.toml").open("rb") as handle:
        config = tomllib.load(handle)
    source = config["public_membership"]
    universe = config["universe"]
    raw_path = PROJECT_ROOT / "data/raw/public_index_history/nasdaq100_components_history.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(source["url"], timeout=30.0)
    response.raise_for_status()
    raw_path.write_bytes(response.content)
    verify_sha256(raw_path, source["sha256"])

    sparse = normalize_sparse_component_history(pd.read_csv(raw_path))
    sparse = sparse[sparse["snapshot_date"].le(universe["evaluation_end"])].copy()
    daily = expand_monthly_membership(
        sparse,
        start=universe["snapshot_start"],
        end=universe["evaluation_end"],
    )
    output_dir = PROJECT_ROOT / "data/interim/ndx"
    output_dir.mkdir(parents=True, exist_ok=True)
    sparse.to_csv(
        output_dir / "ndx_public_membership_snapshots.csv.gz",
        index=False,
        compression="gzip",
    )
    daily.to_csv(PROJECT_ROOT / config["data"]["membership_path"], index=False, compression="gzip")

    ptdata_path = output_dir / "ndx_membership_snapshots.csv.gz"
    overlap = pd.DataFrame()
    if ptdata_path.exists():
        ptdata = pd.read_csv(ptdata_path, parse_dates=["snapshot_date"])
        overlap = comparison(sparse, ptdata)
        overlap.to_csv(output_dir / "public_vs_ptdata.csv", index=False)
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "source_repository": "https://github.com/thuningxu/sp500nq100",
        "source_revision": source["revision"],
        "source_sha256": source["sha256"],
        "source_method": "Backward reconstruction from public constituent-change tables",
        "redistributed": False,
        "first_source_snapshot": str(sparse["snapshot_date"].min().date()),
        "last_source_snapshot": str(sparse["snapshot_date"].max().date()),
        "effective_snapshots": int(sparse["snapshot_date"].nunique()),
        "unique_tickers": int(sparse["ticker"].nunique()),
        "daily_membership_rows": len(daily),
        "ptdata_overlap_snapshots": len(overlap),
        "mean_ptdata_jaccard": float(overlap["jaccard"].mean()) if not overlap.empty else None,
        "minimum_ptdata_jaccard": float(overlap["jaccard"].min()) if not overlap.empty else None,
        "limitations": [
            "Community reconstruction from public sources, not licensed official index history.",
            "The final roster is carried forward after the last recorded effective-date change.",
            "PtData comparisons can differ in change months because its month-end response may lag effective changes.",
        ],
    }
    (output_dir / "public_membership_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
