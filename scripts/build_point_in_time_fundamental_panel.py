from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from run_alpha_research import load_alpha_config, load_modern_panel

from risk_managed_momentum.config import load_config
from risk_managed_momentum.features.alpha import build_alpha_dataset
from risk_managed_momentum.features.sec_fundamentals import (
    FUNDAMENTAL_FEATURES,
    add_accounting_group_ranks,
    assign_point_in_time_cik,
    point_in_time_filing_join,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = PROJECT_ROOT / "data/processed/fundamentals/point_in_time_alpha_panel.csv.gz"
AUDIT_PATH = PROJECT_ROOT / "reports/tables/v14_point_in_time_fundamental_audit.json"


def load_config_v14() -> dict:
    path = PROJECT_ROOT / "configs/research_v1_4_point_in_time_fundamentals.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle)


def build_panel() -> tuple[pd.DataFrame, dict]:
    base = load_config(PROJECT_ROOT / "configs/research.toml")
    alpha_config = load_alpha_config()
    config = load_config_v14()
    price, volume, membership = load_modern_panel(base)
    # Rank fundamentals on the investable signal-date universe before removing rows whose
    # forward return is unavailable. This prevents outcome availability from changing ranks.
    alpha = build_alpha_dataset(
        price, volume, base, alpha_config, membership, include_unlabeled=True
    )
    frame = alpha.frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()

    identities = pd.read_csv(
        PROJECT_ROOT / "data/interim/sec_identity/sp500_sec_identity_intervals.csv"
    )
    annual = pd.read_csv(
        PROJECT_ROOT / "data/interim/sec_fsds_history/annual_fundamentals.csv.gz",
        parse_dates=["filed", "period"],
    )
    identified = assign_point_in_time_cik(frame, identities)
    joined = point_in_time_filing_join(
        identified,
        annual,
        maximum_filing_age_days=int(config["join"]["maximum_filing_age_days"]),
    )
    joined, rank_columns = add_accounting_group_ranks(
        joined,
        minimum_quality_features=int(config["join"]["minimum_quality_features"]),
    )
    joined["filing_age_years"] = joined["filing_age_days"].div(365.25)

    identity_coverage = float(joined["cik"].notna().mean())
    filing_coverage = float(joined["filed"].notna().mean())
    quality_coverage = float(joined["fundamental_quality_score"].notna().mean())
    timing_violations = int((joined["filed"] > joined["date"]).fillna(False).sum())
    by_schema = {}
    for schema, group in joined.dropna(subset=["fundamental_schema"]).groupby(
        "fundamental_schema"
    ):
        by_schema[str(schema)] = {
            "observations": len(group),
            "issuers": int(group["cik"].nunique()),
            "complete_filing_rate": float(group["schema_complete"].fillna(False).mean()),
            "quality_score_rate": float(group["fundamental_quality_score"].notna().mean()),
        }

    sivb = joined[joined["cik"].eq(719739)]
    gates = {
        "signal_identity_coverage": identity_coverage
        >= float(config["join"]["minimum_signal_identity_coverage"]),
        "signal_filing_coverage": filing_coverage
        >= float(config["join"]["minimum_signal_filing_coverage"]),
        "no_future_filing_leakage": timing_violations == 0,
    }
    audit = {
        "specification_version": config["project"]["specification_version"],
        "panel_rows": len(joined),
        "months": int(joined["date"].nunique()),
        "date_range": [str(joined["date"].min().date()), str(joined["date"].max().date())],
        "tickers": int(joined["ticker"].nunique()),
        "issuers": int(joined["cik"].nunique()),
        "identity_coverage": identity_coverage,
        "filing_coverage_after_550_day_expiry": filing_coverage,
        "quality_score_coverage": quality_coverage,
        "stale_filing_observations_expired": int(joined["filing_is_stale"].fillna(False).sum()),
        "timing_violations": timing_violations,
        "feature_coverage": {
            feature: float(joined[feature].notna().mean()) for feature in FUNDAMENTAL_FEATURES
        },
        "accounting_schema_coverage": by_schema,
        "sector_source_counts": {
            str(key): int(value)
            for key, value in joined["sector_source"].fillna("unavailable").value_counts().items()
        },
        "historical_sector_policy": config["ranking"]["historical_sector_policy"],
        "rank_columns": rank_columns,
        "known_sivb_gap": {
            "signal_observations": len(sivb),
            "observations_without_filing": int(sivb["filed"].isna().sum()),
            "treatment": "Missing values are retained; no later filing is backfilled into an earlier date.",
        },
        "gates": gates,
        "panel_gate_passed": all(gates.values()),
        "decision": (
            "enable_frozen_walk_forward_ablation"
            if all(gates.values())
            else "keep_fundamental_model_disabled"
        ),
    }
    return joined, audit


def main() -> None:
    panel, audit = build_panel()
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(PANEL_PATH, index=False, compression={"method": "gzip", "mtime": 0})
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
