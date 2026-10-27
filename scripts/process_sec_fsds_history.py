from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.sec_fsds import (
    FUNDAMENTAL_SCHEMAS,
    assign_historical_fundamental_schema,
    parse_fsds_archive,
)
from risk_managed_momentum.data.sec_identity import (
    attach_interval_names,
    build_sec_identity_map,
    carry_forward_resolved_identities,
    load_fsds_submission_registry,
    load_sec_ticker_registry,
    membership_intervals,
    resolve_identity_names,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERIOD_PATTERN = re.compile(r"(20\d{2}q[1-4])", re.IGNORECASE)
DATE_COLUMNS = ("period", "filed", "prior_assets_date", "prior_revenue_date")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process official SEC quarterly archives into a resumable fundamentals panel."
    )
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def archive_period(path: Path) -> str:
    match = PERIOD_PATTERN.search(path.name)
    if not match:
        raise ValueError(f"Archive name must contain a period such as 2024q1: {path}")
    return match.group(1).lower()


def identity_manifest(identities: pd.DataFrame, periods: list[str]) -> dict[str, object]:
    resolved = identities["status"].eq("RESOLVED")
    interval_coverage = float(resolved.mean())
    day_coverage = float(
        identities.loc[resolved, "membership_days"].sum() / identities["membership_days"].sum()
    )
    return {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "archives_used_for_names": periods,
        "intervals": len(identities),
        "unique_tickers": int(identities["ticker"].nunique()),
        "resolved_intervals": int(resolved.sum()),
        "review_intervals": int((~resolved).sum()),
        "interval_coverage": interval_coverage,
        "membership_day_coverage": day_coverage,
        "bulk_download_gate": {
            "minimum_membership_day_coverage": 0.90,
            "passes": bool(day_coverage >= 0.90),
        },
        "model_enablement_gate": {
            "minimum_interval_coverage": 0.95,
            "passes": bool(interval_coverage >= 0.95),
        },
    }


def build_identities(archives: list[Path]) -> tuple[pd.DataFrame, dict[str, object]]:
    membership_dir = PROJECT_ROOT / "data/interim/membership"
    current = pd.read_csv(membership_dir / "sp500_v12_current_components.csv")
    changes = pd.read_csv(membership_dir / "sp500_v12_changes.csv")
    daily = pd.read_csv(membership_dir / "sp500_v12_daily_membership.csv.gz", parse_dates=["date"])
    registry = load_sec_ticker_registry(PROJECT_ROOT / "data/raw/sec/company_tickers.json")
    intervals = attach_interval_names(membership_intervals(daily), current, changes)
    identities = build_sec_identity_map(intervals, current, registry)
    identity_dir = PROJECT_ROOT / "data/interim/sec_identity"
    previous_path = identity_dir / "sp500_sec_identity_intervals.csv"
    prior_periods: list[str] = []
    if previous_path.is_file():
        identities = carry_forward_resolved_identities(identities, pd.read_csv(previous_path))
        previous_manifest_path = identity_dir / "manifest.json"
        if previous_manifest_path.is_file():
            prior_periods = json.loads(previous_manifest_path.read_text()).get(
                "archives_used_for_names", []
            )
    filing_entities = pd.concat(
        [load_fsds_submission_registry(path) for path in archives], ignore_index=True
    ).drop_duplicates(["cik", "normalized_name", "filed"])
    identities = resolve_identity_names(identities, filing_entities)
    periods = sorted(set(prior_periods) | {archive_period(path) for path in archives})
    return identities, identity_manifest(identities, periods)


def schema_coverage(frame: pd.DataFrame) -> dict[str, object]:
    return {
        schema: {
            "filings": int(frame["fundamental_schema"].eq(schema).sum()),
            "complete_coverage": float(
                frame.loc[frame["fundamental_schema"].eq(schema), "schema_complete"].mean()
            ),
            "features": list(features),
        }
        for schema, features in FUNDAMENTAL_SCHEMAS.items()
        if frame["fundamental_schema"].eq(schema).any()
    }


def normalize_dates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in DATE_COLUMNS:
        if column in result:
            result[column] = pd.to_datetime(result[column], errors="coerce", format="mixed")
    return result


def main() -> None:
    args = parse_args()
    archives = sorted((path.expanduser().resolve() for path in args.archives), key=archive_period)
    missing = [str(path) for path in archives if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing SEC archives: {missing}")

    identities, identity_summary = build_identities(archives)
    identity_dir = PROJECT_ROOT / "data/interim/sec_identity"
    identity_dir.mkdir(parents=True, exist_ok=True)
    identities.to_csv(identity_dir / "sp500_sec_identity_intervals.csv", index=False)
    identities[identities["status"].ne("RESOLVED")].to_csv(
        identity_dir / "sp500_sec_identity_review_queue.csv", index=False
    )
    (identity_dir / "manifest.json").write_text(json.dumps(identity_summary, indent=2) + "\n")

    resolved_ciks = identities.loc[identities["status"].eq("RESOLVED"), "cik"].dropna().astype(int)
    current = pd.read_csv(PROJECT_ROOT / "data/interim/membership/sp500_v12_current_components.csv")
    output_dir = PROJECT_ROOT / "data/interim/sec_fsds_history"
    output_dir.mkdir(parents=True, exist_ok=True)
    for archive in archives:
        period = archive_period(archive)
        output = output_dir / f"{period}.csv.gz"
        manifest_path = output_dir / f"{period}_manifest.json"
        if output.exists() and manifest_path.exists() and not args.force:
            normalized = normalize_dates(pd.read_csv(output))
            quarter_summary = json.loads(manifest_path.read_text())
        else:
            normalized = normalize_dates(parse_fsds_archive(archive, resolved_ciks))
            normalized = assign_historical_fundamental_schema(normalized, current)
            normalized.to_csv(output, index=False, compression="gzip")
            quarter_summary = {
                "processed_at_utc": datetime.now(UTC).isoformat(),
                "period": period,
                "source": "SEC Financial Statement Data Sets",
                "filings": len(normalized),
                "issuers": int(normalized["cik"].nunique()),
                "actual_filing_dates": True,
                "sector_source_counts": {
                    str(key): int(value)
                    for key, value in normalized["sector_source"].value_counts().items()
                },
                "schema_coverage": schema_coverage(normalized),
                "output": str(output.relative_to(PROJECT_ROOT)),
            }
            manifest_path.write_text(json.dumps(quarter_summary, indent=2) + "\n")
    period_outputs = [
        normalize_dates(pd.read_csv(path)) for path in sorted(output_dir.glob("20??q?.csv.gz"))
    ]
    quarter_summaries = [
        json.loads(path.read_text()) for path in sorted(output_dir.glob("20??q?_manifest.json"))
    ]
    history = pd.concat(period_outputs, ignore_index=True)
    history = history.sort_values(["cik", "filed", "adsh"]).drop_duplicates("adsh")
    history.to_csv(output_dir / "annual_fundamentals.csv.gz", index=False, compression="gzip")
    history_summary = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "periods": [summary["period"] for summary in quarter_summaries],
        "filings": len(history),
        "issuers": int(history["cik"].nunique()),
        "quality": {
            "duplicate_accessions": int(history["adsh"].duplicated().sum()),
            "unparsed_filing_or_period_dates": int(
                history[["filed", "period"]].isna().any(axis=1).sum()
            ),
            "filings_before_period_end": int((history["filed"] < history["period"]).sum()),
            "minimum_filing_date": history["filed"].min().date().isoformat(),
            "maximum_filing_date": history["filed"].max().date().isoformat(),
        },
        "identity": identity_summary,
        "schema_coverage": schema_coverage(history),
        "historical_sector_limitation": (
            "Current constituents use current GICS. Former constituents use SEC SIC only to select "
            "an accounting schema; a historical sector source is still required for sector ranking."
        ),
        "model_enabled": False,
    }
    (output_dir / "manifest.json").write_text(json.dumps(history_summary, indent=2) + "\n")
    print(json.dumps(history_summary, indent=2))


if __name__ == "__main__":
    main()
