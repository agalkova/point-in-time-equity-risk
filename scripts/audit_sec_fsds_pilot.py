from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from risk_managed_momentum.data.sec_fsds import FUNDAMENTAL_SCHEMAS, assign_fundamental_schema

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
    "gross_margin",
    "operating_margin",
    "cash_flow_margin",
    "return_on_assets",
    "liabilities_to_assets",
    "asset_growth",
]
RANGES = {
    "gross_margin": (-2.0, 2.0),
    "operating_margin": (-2.0, 2.0),
    "cash_flow_margin": (-5.0, 5.0),
    "return_on_assets": (-2.0, 2.0),
    "liabilities_to_assets": (-1.0, 2.0),
    "asset_growth": (-1.0, 10.0),
    "net_margin": (-5.0, 5.0),
    "equity_to_assets": (-2.0, 2.0),
    "cash_flow_to_assets": (-2.0, 2.0),
    "revenue_growth": (-1.0, 10.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the direct-SEC FSDS pilot")
    parser.add_argument("--period", default="2024q1")
    return parser.parse_args()


def close(expected: pd.Series, actual: pd.Series) -> pd.Series:
    return pd.Series(
        np.isclose(expected, actual, rtol=1e-10, atol=1e-12, equal_nan=True),
        index=actual.index,
    )


def main() -> None:
    args = parse_args()
    period = args.period.lower()
    frame = pd.read_csv(
        PROJECT_ROOT / f"data/interim/sec_fsds/pilot_{period}.csv.gz",
        parse_dates=["period", "filed", "prior_assets_date", "prior_revenue_date"],
    )
    frame = assign_fundamental_schema(frame)
    lag_days = (frame["filed"] - frame["period"]).dt.days
    revenue = frame["revenue"].where(frame["revenue"].abs() > 1e-12)
    average_assets = frame[["assets", "prior_assets"]].mean(axis=1, skipna=False)
    reconciliations = {
        "gross_margin": close(frame["gross_profit"] / revenue, frame["gross_margin"]),
        "operating_margin": close(frame["operating_income"] / revenue, frame["operating_margin"]),
        "cash_flow_margin": close(
            frame["operating_cash_flow"] / revenue, frame["cash_flow_margin"]
        ),
        "return_on_assets": close(frame["net_income"] / average_assets, frame["return_on_assets"]),
        "liabilities_to_assets": close(
            frame["liabilities"] / frame["assets"], frame["liabilities_to_assets"]
        ),
        "asset_growth": close(frame["assets"] / frame["prior_assets"] - 1.0, frame["asset_growth"]),
        "net_margin": close(frame["net_income"] / revenue, frame["net_margin"]),
        "equity_to_assets": close(frame["equity"] / frame["assets"], frame["equity_to_assets"]),
        "cash_flow_to_assets": close(
            frame["operating_cash_flow"] / average_assets, frame["cash_flow_to_assets"]
        ),
        "revenue_growth": close(
            frame["revenue"] / frame["prior_revenue"] - 1.0, frame["revenue_growth"]
        ),
    }
    range_flags = pd.DataFrame(
        {
            feature: frame[feature].notna()
            & ~frame[feature].between(lower, upper, inclusive="both")
            for feature, (lower, upper) in RANGES.items()
        }
    )
    complete = frame[FEATURES].notna().all(axis=1)
    nonfinancial = ~frame["sector"].isin(["Financials", "Real Estate"])
    report = {
        "audited_at_utc": datetime.now(UTC).isoformat(),
        "period": period,
        "rows": len(frame),
        "unique_issuers": int(frame["cik"].nunique()),
        "sectors": int(frame["sector"].nunique()),
        "duplicate_accessions": int(frame["adsh"].duplicated().sum()),
        "filing_date_checks": {
            "filed_before_period_end": int((lag_days < 0).sum()),
            "filed_more_than_120_days_after_period_end": int((lag_days > 120).sum()),
            "minimum_lag_days": int(lag_days.min()),
            "median_lag_days": float(lag_days.median()),
            "maximum_lag_days": int(lag_days.max()),
        },
        "feature_coverage": {feature: float(frame[feature].notna().mean()) for feature in FEATURES},
        "all_six_coverage": float(complete.mean()),
        "nonfinancial_all_six_coverage": float(complete[nonfinancial].mean()),
        "sector_schema_coverage": {
            schema: {
                "issuers": int(frame["fundamental_schema"].eq(schema).sum()),
                "complete_coverage": float(
                    frame.loc[frame["fundamental_schema"].eq(schema), "schema_complete"].mean()
                ),
                "features": list(features),
            }
            for schema, features in FUNDAMENTAL_SCHEMAS.items()
        },
        "reconciliation_failures": {
            feature: int((~checks).sum()) for feature, checks in reconciliations.items()
        },
        "economic_range_flags": {feature: int(range_flags[feature].sum()) for feature in RANGES},
        "universal_schema_passes_50pct_gate": bool(complete.mean() >= 0.5),
        "nonfinancial_schema_passes_50pct_gate": bool(complete[nonfinancial].mean() >= 0.5),
        "decision": (
            "Use the frozen sector-aware schemas for coverage validation. Keep the fundamental "
            "model disabled until historical identity and feature gates pass."
        ),
    }
    output = PROJECT_ROOT / f"reports/tables/sec_fsds_{period}_pilot_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
