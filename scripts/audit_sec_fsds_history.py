from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.sec_fsds import FUNDAMENTAL_SCHEMAS

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def quarterly_periods(first_year: int, last_year: int, last_quarter: int) -> list[str]:
    return [
        f"{year}q{quarter}"
        for year in range(first_year, last_year + 1)
        for quarter in range(1, (last_quarter if year == last_year else 4) + 1)
    ]


def main() -> None:
    history_dir = PROJECT_ROOT / "data/interim/sec_fsds_history"
    history = pd.read_csv(history_dir / "annual_fundamentals.csv.gz")
    for column in ["period", "filed", "prior_assets_date", "prior_revenue_date"]:
        history[column] = pd.to_datetime(history[column], errors="coerce", format="mixed")
    identity_manifest = json.loads(
        (PROJECT_ROOT / "data/interim/sec_identity/manifest.json").read_text()
    )
    processed = sorted(
        path.name.removesuffix("_manifest.json")
        for path in history_dir.glob("20??q?_manifest.json")
    )
    expected = quarterly_periods(2014, 2026, 3)
    missing_periods = [period for period in expected if period not in processed]
    identity_passes = bool(identity_manifest["model_enablement_gate"]["passes"])
    schema_passes = {
        schema: bool(
            history.loc[history["fundamental_schema"].eq(schema), list(features)]
            .notna()
            .all(axis=1)
            .mean()
            >= 0.50
        )
        for schema, features in FUNDAMENTAL_SCHEMAS.items()
    }
    archive_gate_passes = not missing_periods and identity_passes and all(schema_passes.values())
    report = {
        "audited_at_utc": datetime.now(UTC).isoformat(),
        "processed_periods": processed,
        "missing_periods_through_2026q3": missing_periods,
        "filings": len(history),
        "issuers": int(history["cik"].nunique()),
        "quality": {
            "duplicate_accessions": int(history["adsh"].duplicated().sum()),
            "unparsed_filing_or_period_dates": int(
                history[["filed", "period"]].isna().any(axis=1).sum()
            ),
            "filings_before_period_end": int((history["filed"] < history["period"]).sum()),
        },
        "identity": identity_manifest,
        "gates": {
            "complete_archive_history": not missing_periods,
            "identity_interval_coverage": identity_passes,
            "schema_complete_coverage": schema_passes,
            "archive_stage_passes": archive_gate_passes,
        },
        "schema_coverage": {
            schema: {
                "filings": int(history["fundamental_schema"].eq(schema).sum()),
                "feature_coverage": {
                    feature: float(
                        history.loc[history["fundamental_schema"].eq(schema), feature]
                        .notna()
                        .mean()
                    )
                    for feature in features
                },
                "complete_coverage": float(
                    history.loc[history["fundamental_schema"].eq(schema), list(features)]
                    .notna()
                    .all(axis=1)
                    .mean()
                ),
            }
            for schema, features in FUNDAMENTAL_SCHEMAS.items()
        },
        "decision": (
            "Archive and coverage gates pass. Advance to point-in-time panel construction, but keep "
            "the model disabled until as-of joins, historical sector treatment, and known issuer "
            "backfill gaps are audited."
            if archive_gate_passes
            else "Continue archive or coverage remediation; do not enable the fundamental model."
        ),
    }
    output = PROJECT_ROOT / "reports/tables/sec_fsds_history_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
