from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.sec_fsds import (
    FUNDAMENTAL_SCHEMAS,
    assign_fundamental_schema,
    download_fsds_archive,
    feature_coverage,
    parse_fsds_archive,
    read_submissions,
    resolve_sec_user_agent,
    select_sector_pilot,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "gross_margin",
    "operating_margin",
    "cash_flow_margin",
    "return_on_assets",
    "liabilities_to_assets",
    "asset_growth",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a one-quarter SEC FSDS pilot")
    parser.add_argument("--period", default="2024q1")
    parser.add_argument("--companies", type=int, default=30)
    parser.add_argument("--user-agent")
    parser.add_argument(
        "--archive-path",
        type=Path,
        help="Use an already-downloaded official SEC ZIP and leave it untouched",
    )
    parser.add_argument("--keep-archive", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    components = pd.read_csv(
        PROJECT_ROOT / "data/interim/membership/sp500_v12_current_components.csv"
    )
    managed_archive = args.archive_path is None
    raw_path = (
        PROJECT_ROOT / f"data/raw/sec/fsds/{args.period.lower()}.zip"
        if managed_archive
        else args.archive_path.expanduser().resolve()
    )
    if managed_archive and not raw_path.exists():
        user_agent = resolve_sec_user_agent(args.user_agent)
        download_fsds_archive(args.period, raw_path, user_agent=user_agent)
    if not raw_path.is_file():
        raise FileNotFoundError(raw_path)
    available_submissions = read_submissions(raw_path, components["cik"])
    eligible = components.merge(
        available_submissions[["cik"]].drop_duplicates(),
        on="cik",
        how="inner",
        validate="many_to_one",
    ).drop_duplicates("cik")
    pilot = select_sector_pilot(eligible, args.companies)
    normalized = parse_fsds_archive(raw_path, pilot["cik"])
    normalized = normalized.merge(
        pilot[["ticker", "security", "sector", "cik"]],
        on="cik",
        how="left",
        validate="many_to_one",
    )
    normalized = assign_fundamental_schema(normalized)
    output_dir = PROJECT_ROOT / "data/interim/sec_fsds"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"pilot_{args.period.lower()}.csv.gz"
    normalized.to_csv(output_path, index=False, compression="gzip")
    coverage = feature_coverage(normalized, FEATURES)
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "source": "SEC Financial Statement Data Sets",
        "period": args.period.lower(),
        "selection": (
            "deterministic round-robin across current GICS sectors among issuers "
            "with 10-K filings in the quarter"
        ),
        "eligible_current_issuers": int(eligible["cik"].nunique()),
        "requested_companies": len(pilot),
        "requested_sectors": int(pilot["sector"].nunique()),
        **coverage,
        "sector_schema_coverage": {
            schema: {
                "issuers": int(normalized["fundamental_schema"].eq(schema).sum()),
                "complete_coverage": float(
                    normalized.loc[
                        normalized["fundamental_schema"].eq(schema), "schema_complete"
                    ].mean()
                ),
                "features": list(features),
            }
            for schema, features in FUNDAMENTAL_SCHEMAS.items()
        },
        "output_path": str(output_path.relative_to(PROJECT_ROOT)),
        "archive_retained": bool(args.keep_archive or not managed_archive),
    }
    manifest_path = output_dir / f"pilot_{args.period.lower()}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if managed_archive and not args.keep_archive:
        raw_path.unlink()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
