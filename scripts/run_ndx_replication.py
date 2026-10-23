from __future__ import annotations

import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from run_modern_replication import score_summary
from sklearn.base import clone
from sklearn.metrics import average_precision_score, roc_auc_score

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.panel import build_point_in_time_panel, coverage_summary
from risk_managed_momentum.evaluation.ranking import daily_rank_ic, moving_block_interval
from risk_managed_momentum.features.build import build_research_dataset, split_research_dataset
from risk_managed_momentum.models.drawdown import select_logistic_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def limited_subset_summary(frame: pd.DataFrame, config: dict) -> dict[str, object]:
    if frame.empty or frame["target"].nunique() < 2:
        return {"observations": len(frame), "status": "insufficient outcome variation"}
    rank_ic = daily_rank_ic(frame, "risk_score")
    interval = moving_block_interval(
        rank_ic,
        block_length=int(config["inference"]["block_bootstrap_days"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )
    prevalence = float(frame["target"].mean())
    average_precision = float(average_precision_score(frame["target"], frame["risk_score"]))
    return {
        "observations": len(frame),
        "positives": int(frame["target"].sum()),
        "prevalence": prevalence,
        "roc_auc": float(roc_auc_score(frame["target"], frame["risk_score"])),
        "average_precision": average_precision,
        "average_precision_lift": average_precision / prevalence if prevalence else np.nan,
        "rank_ic_days": len(rank_ic),
        "mean_daily_rank_ic": float(rank_ic.mean()),
        "mean_daily_rank_ic_95pct_block_interval": list(interval),
    }


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    with (PROJECT_ROOT / "configs/research_v0_7_ndx.toml").open("rb") as handle:
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
    membership_long = pd.read_csv(PROJECT_ROOT / config["data"]["membership_path"])
    with (PROJECT_ROOT / "data/reference/ndx_symbol_aliases.toml").open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    price, volume, membership = build_point_in_time_panel(bars, membership_long, aliases=aliases)
    coverage = coverage_summary(price, membership)
    ndx_dataset = build_research_dataset(price, volume, base_config, membership=membership)
    if ndx_dataset.feature_columns != legacy_dataset.feature_columns:
        raise RuntimeError("Legacy and NDX feature schemas differ")
    universe = config["universe"]
    frame = ndx_dataset.frame[
        ndx_dataset.frame["date"].between(
            universe["evaluation_start"], universe["evaluation_end"]
        )
    ].copy()
    if frame.empty:
        raise RuntimeError("NDX replication contains no eligible observations")
    frame["risk_score"] = model.predict_proba(frame[ndx_dataset.feature_columns])[:, 1]

    sp500 = pd.read_csv(PROJECT_ROOT / base_config["modern_source"]["membership_path"])
    sp500["date"] = pd.to_datetime(sp500["date"]).dt.normalize()
    sp500["ticker"] = sp500["ticker"].astype(str).str.upper()
    sp500_pairs = pd.MultiIndex.from_frame(sp500[["date", "ticker"]])
    frame_pairs = pd.MultiIndex.from_frame(frame[["date", "ticker"]])
    frame["also_sp500_member"] = frame_pairs.isin(sp500_pairs)

    ndx_daily = membership_long.copy()
    ndx_daily["date"] = pd.to_datetime(ndx_daily["date"]).dt.normalize()
    ndx_daily["ticker"] = ndx_daily["ticker"].astype(str).str.upper()
    overlap = ndx_daily.merge(
        sp500.assign(also_sp500_member=True),
        on=["date", "ticker"],
        how="left",
    )
    overlap["also_sp500_member"] = overlap["also_sp500_member"].fillna(False)
    daily_overlap = overlap.groupby("date").agg(
        ndx_members=("ticker", "nunique"),
        overlapping_members=("also_sp500_member", "sum"),
    )
    daily_overlap["overlap_rate"] = (
        daily_overlap["overlapping_members"] / daily_overlap["ndx_members"]
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
    non_sp500 = limited_subset_summary(frame[~frame["also_sp500_member"]], base_config)
    expected_years = list(
        range(
            pd.Timestamp(universe["evaluation_start"]).year,
            pd.Timestamp(universe["evaluation_end"]).year + 1,
        )
    )
    observed_years = sorted(annual["year"].astype(int).tolist())
    full_evaluation_coverage = observed_years == expected_years
    positive_rank_ic_years = int(annual["mean_daily_rank_ic"].gt(0).sum())
    pass_rule = {
        "roc_auc_above_0_60": primary["roc_auc"] > 0.60,
        "top_to_bottom_risk_ratio_at_least_2": primary["top_to_bottom_risk_ratio"] >= 2.0,
        "rank_ic_positive_interval": primary["mean_daily_rank_ic_95pct_block_interval"][0]
        > 0.0,
        "positive_rank_ic_at_least_six_of_seven_years": (
            positive_rank_ic_years >= 6 if full_evaluation_coverage else None
        ),
    }
    summary = {
        "specification_version": config["project"]["specification_version"],
        "model_selected_on_legacy_validation": selected.name,
        "model_changed_for_ndx": False,
        "membership_snapshot_frequency": universe["snapshot_frequency"],
        "evaluation_first_signal": str(frame["date"].min().date()),
        "evaluation_last_signal": str(frame["date"].max().date()),
        "data_coverage": {
            "expected_evaluation_years": expected_years,
            "observed_evaluation_years": observed_years,
            "full_evaluation_coverage": full_evaluation_coverage,
            "positive_rank_ic_years_observed": positive_rank_ic_years,
            "coverage_status": (
                "complete" if full_evaluation_coverage else "incomplete_provider_history"
            ),
        },
        "membership_tickers": int(membership.shape[1]),
        "median_membership_price_coverage": float(coverage["coverage_rate"].median()),
        "mean_daily_sp500_overlap": float(daily_overlap["overlap_rate"].mean()),
        "primary_ndx_results": primary,
        "non_sp500_member_diagnostic": non_sp500,
        "pass_rule": pass_rule,
        "passed": all(pass_rule.values()) if full_evaluation_coverage else None,
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(TABLES / "v07_ndx_membership_coverage.csv", index=False)
    annual.to_csv(TABLES / "v07_ndx_annual.csv", index=False)
    daily_overlap.reset_index().to_csv(TABLES / "v07_ndx_sp500_overlap.csv", index=False)
    frame[
        [
            "date",
            "ticker",
            "target",
            "future_min_return",
            "risk_score",
            "also_sp500_member",
        ]
    ].to_csv(TABLES / "v07_ndx_predictions.csv.gz", index=False, compression="gzip")
    (TABLES / "v07_ndx_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
