from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from run_modern_replication import score_summary
from sklearn.base import clone

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.panel import build_point_in_time_panel, coverage_summary
from risk_managed_momentum.features.build import build_research_dataset, split_research_dataset
from risk_managed_momentum.models.drawdown import select_logistic_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    with (PROJECT_ROOT / "configs/research_v0_8_sp400.toml").open("rb") as handle:
        config = tomllib.load(handle)

    legacy_price, legacy_volume = load_legacy_wide(
        base_config["legacy_source"]["price_path"],
        base_config["legacy_source"]["volume_path"],
    )
    legacy_dataset = build_research_dataset(legacy_price, legacy_volume, base_config)
    legacy_splits = split_research_dataset(legacy_dataset, base_config)
    selected = select_logistic_model(
        legacy_splits["train"],
        legacy_splits["validation"],
        legacy_dataset.feature_columns,
        random_seed=int(base_config["project"]["random_seed"]),
    )
    development = pd.concat(legacy_splits.values(), ignore_index=True)
    model = clone(selected.model).fit(
        development[legacy_dataset.feature_columns], development["target"]
    )

    bars = pd.read_csv(PROJECT_ROOT / config["data"]["bars_path"])
    gap_path = PROJECT_ROOT / config["data"]["historical_gap_bars_path"]
    if gap_path.exists():
        gap_bars = pd.read_csv(gap_path)
        bars = pd.concat([bars, gap_bars[bars.columns]], ignore_index=True)
    membership_long = pd.read_csv(PROJECT_ROOT / config["data"]["membership_path"])
    with (PROJECT_ROOT / "data/reference/sp400_symbol_aliases.toml").open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    price, volume, membership = build_point_in_time_panel(
        bars, membership_long, aliases=aliases
    )
    coverage = coverage_summary(price, membership)
    minimum_coverage = float(config["quality_gates"]["minimum_median_price_coverage"])
    median_coverage = float(coverage["coverage_rate"].median())
    membership_manifest = json.loads(
        (PROJECT_ROOT / "data/interim/sp400/manifest.json").read_text()
    )
    quality_gates = {
        "current_roster_jaccard_at_least_minimum": bool(
            membership_manifest["quality_gate_passed"]
        ),
        "median_price_coverage_at_least_minimum": median_coverage >= minimum_coverage,
    }
    if not all(quality_gates.values()):
        raise RuntimeError(f"S&P 400 pre-evaluation quality gates failed: {quality_gates}")

    dataset = build_research_dataset(price, volume, base_config, membership=membership)
    if dataset.feature_columns != legacy_dataset.feature_columns:
        raise RuntimeError("Legacy and S&P 400 feature schemas differ")
    universe = config["universe"]
    frame = dataset.frame[
        dataset.frame["date"].between(universe["evaluation_start"], universe["evaluation_end"])
    ].copy()
    if frame.empty:
        raise RuntimeError("S&P 400 replication contains no eligible observations")
    frame["risk_score"] = model.predict_proba(frame[dataset.feature_columns])[:, 1]

    sp500 = pd.read_csv(PROJECT_ROOT / base_config["modern_source"]["membership_path"])
    sp500["date"] = pd.to_datetime(sp500["date"]).dt.normalize()
    sp500["ticker"] = sp500["ticker"].astype(str).str.upper()
    overlap = membership_long.copy()
    overlap["date"] = pd.to_datetime(overlap["date"]).dt.normalize()
    overlap["ticker"] = overlap["ticker"].astype(str).str.upper()
    overlap = overlap.merge(
        sp500.assign(also_sp500_member=True), on=["date", "ticker"], how="left"
    )
    overlap["also_sp500_member"] = overlap["also_sp500_member"].fillna(False)
    daily_overlap = overlap.groupby("date").agg(
        sp400_members=("ticker", "nunique"),
        overlapping_members=("also_sp500_member", "sum"),
    )
    daily_overlap["overlap_rate"] = (
        daily_overlap["overlapping_members"] / daily_overlap["sp400_members"]
    )

    primary = score_summary(frame, "risk_score", base_config)
    annual_rows = []
    for year, group in frame.groupby(frame["date"].dt.year):
        result = score_summary(group, "risk_score", base_config)
        annual_rows.append(
            {
                "year": int(year),
                "observations": result["observations"],
                "prevalence": result["prevalence"],
                "average_precision": result["average_precision"],
                "roc_auc": result["roc_auc"],
                "mean_daily_rank_ic": result["mean_daily_rank_ic"],
                "top_minus_bottom_event_rate": result["top_minus_bottom_event_rate"],
            }
        )
    annual = pd.DataFrame(annual_rows)
    rules = config["pass_rule"]
    pass_rule = {
        "roc_auc_above_0_60": primary["roc_auc"] > float(rules["minimum_roc_auc"]),
        "average_precision_lift_at_least_1_25": primary["average_precision_lift"]
        >= float(rules["minimum_average_precision_lift"]),
        "top_to_bottom_risk_ratio_at_least_2": primary["top_to_bottom_risk_ratio"]
        >= float(rules["minimum_top_bottom_risk_ratio"]),
        "rank_ic_positive_interval": primary["mean_daily_rank_ic_95pct_block_interval"][0]
        > 0.0,
        "positive_rank_ic_at_least_six_years": int(
            annual["mean_daily_rank_ic"].gt(0).sum()
        )
        >= int(rules["minimum_positive_rank_ic_years"]),
    }
    summary = {
        "specification_version": config["project"]["specification_version"],
        "model_selected_on_legacy_validation": selected.name,
        "model_changed_for_sp400": False,
        "evaluation_first_signal": str(frame["date"].min().date()),
        "evaluation_last_signal": str(frame["date"].max().date()),
        "observations": len(frame),
        "membership_tickers": int(membership.shape[1]),
        "median_membership_price_coverage": median_coverage,
        "mean_daily_sp500_overlap": float(daily_overlap["overlap_rate"].mean()),
        "quality_gates": quality_gates,
        "primary_sp400_results": primary,
        "annual_positive_rank_ic_years": int(annual["mean_daily_rank_ic"].gt(0).sum()),
        "pass_rule": pass_rule,
        "passed": all(quality_gates.values()) and all(pass_rule.values()),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(TABLES / "v08_sp400_membership_coverage.csv", index=False)
    annual.to_csv(TABLES / "v08_sp400_annual.csv", index=False)
    daily_overlap.reset_index().to_csv(TABLES / "v08_sp400_sp500_overlap.csv", index=False)
    frame[["date", "ticker", "target", "future_min_return", "risk_score"]].to_csv(
        TABLES / "v08_sp400_predictions.csv.gz", index=False, compression="gzip"
    )
    (TABLES / "v08_sp400_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
