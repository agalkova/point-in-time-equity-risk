from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from risk_managed_momentum.data.ndx import expand_monthly_membership, verify_sha256
from risk_managed_momentum.data.sp400 import build_event_sourced_snapshots, roster_jaccard

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_EXCLUSIONS = {"TEMPLATE:INVESTORS EXCHANGE LINK"}


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_8_sp400.toml").open("rb") as handle:
        config = tomllib.load(handle)
    source = config["public_membership"]
    raw_dir = PROJECT_ROOT / "data/raw/pitindex/sp400"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = {}
    for name in ("seed", "changes", "current"):
        path = raw_dir / f"sp400_{name}.csv"
        response = requests.get(source[f"{name}_url"], timeout=30.0)
        response.raise_for_status()
        path.write_bytes(response.content)
        verify_sha256(path, source[f"{name}_sha256"])
        frames[name] = pd.read_csv(path)

    universe = config["universe"]
    clean_seed = frames["seed"][~frames["seed"]["ticker"].isin(SOURCE_EXCLUSIONS)].copy()
    clean_changes = frames["changes"][
        ~frames["changes"]["ticker"].isin(SOURCE_EXCLUSIONS)
    ].copy()
    snapshots = build_event_sourced_snapshots(
        clean_seed,
        clean_changes,
        start=universe["membership_start"],
        end=universe["evaluation_end"],
    )
    daily = expand_monthly_membership(
        snapshots,
        start=universe["membership_start"],
        end=universe["evaluation_end"],
    )
    last_date = snapshots["snapshot_date"].max()
    reconstructed = set(snapshots.loc[snapshots["snapshot_date"].eq(last_date), "ticker"])
    current = set(frames["current"]["ticker"].astype(str).str.upper())
    current_jaccard = roster_jaccard(reconstructed, current)
    minimum_jaccard = float(config["quality_gates"]["minimum_current_roster_jaccard"])
    if current_jaccard < minimum_jaccard:
        raise RuntimeError(
            f"S&P 400 roster reconciliation {current_jaccard:.4f} is below {minimum_jaccard:.4f}"
        )

    output_dir = PROJECT_ROOT / "data/interim/sp400"
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshots.to_csv(
        output_dir / "sp400_membership_snapshots.csv.gz", index=False, compression="gzip"
    )
    daily.to_csv(output_dir / "sp400_daily_membership.csv.gz", index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "source_repository": source["repository"],
        "source_revision": source["revision"],
        "source_files_sha256": {
            name: source[f"{name}_sha256"] for name in ("seed", "changes", "current")
        },
        "source_method": "Public change tables plus conservatively dated revision-history diffs",
        "excluded_source_artifacts": sorted(SOURCE_EXCLUSIONS),
        "redistributed": False,
        "effective_snapshots": int(snapshots["snapshot_date"].nunique()),
        "unique_tickers": int(snapshots["ticker"].nunique()),
        "daily_membership_rows": len(daily),
        "last_snapshot": str(pd.Timestamp(last_date).date()),
        "last_snapshot_size": len(reconstructed),
        "pinned_current_size": len(current),
        "current_roster_jaccard": current_jaccard,
        "minimum_required_jaccard": minimum_jaccard,
        "quality_gate_passed": current_jaccard >= minimum_jaccard,
        "limitations": [
            "Community reconstruction, not licensed official S&P constituent history.",
            "Revision-derived event dates can lag true effective dates by up to roughly one month.",
            "Historical ticker identity is best effort and requires price-coverage auditing.",
            "One explicit Wikipedia-template artifact is excluded; it is not a security ticker.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
