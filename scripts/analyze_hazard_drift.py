from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.universes import load_sp500_panel
from risk_managed_momentum.evaluation.hazard import episode_score_summary
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import (
    fit_hazard_model,
    predict_cumulative_risk,
    standardized_coefficients,
)
from risk_managed_momentum.operations.monitoring import population_stability_index
from risk_managed_momentum.operations.registry import load_active_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"
FIGURES = PROJECT_ROOT / "docs/figures"


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    hazard_config = load_toml(
        PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml"
    )
    challenger_config = load_toml(
        PROJECT_ROOT / "configs/research_v1_1_hazard_challenger.toml"
    )
    champion, metadata, _ = load_active_model(
        PROJECT_ROOT / "reports/operations/model_registry"
    )
    price, volume, membership = load_sp500_panel(PROJECT_ROOT, base_config)
    labeled = build_exuberance_episode_dataset(
        price,
        volume,
        base_config,
        hazard_config,
        membership=membership,
    )
    live = build_exuberance_episode_dataset(
        price,
        volume,
        base_config,
        hazard_config,
        membership=membership,
        include_unlabeled=True,
    )
    rolling_training = labeled.frame[labeled.frame["date"].between(
        challenger_config["data"]["rolling_training_start"],
        challenger_config["data"]["expanding_training_end"],
    )].copy()
    challenger = fit_hazard_model(
        rolling_training,
        labeled.feature_columns,
        hazard_config["outcome"]["horizon_end_days"],
        c=float(challenger_config["model"]["c"]),
        maximum_iterations=int(challenger_config["model"]["maximum_iterations"]),
        random_seed=int(challenger_config["project"]["random_seed"]),
    )
    champion_scored = predict_cumulative_risk(champion, live.frame)
    challenger_scored = predict_cumulative_risk(challenger, live.frame)
    reference_mask = live.frame["date"].between(
        challenger_config["drift"]["reference_start"],
        challenger_config["drift"]["reference_end"],
    )
    recent_cutoff = pd.Timestamp(price.index.max()) - pd.Timedelta(
        days=int(challenger_config["drift"]["recent_calendar_days"])
    )
    recent_mask = live.frame["date"].ge(recent_cutoff)
    bins = int(challenger_config["drift"]["bins"])

    champion_coefficients = standardized_coefficients(champion).set_index("feature")
    challenger_coefficients = standardized_coefficients(challenger).set_index("feature")
    feature_rows = []
    for feature in live.feature_columns:
        reference = live.frame.loc[reference_mask, feature]
        recent = live.frame.loc[recent_mask, feature]
        reference_std = float(reference.std())
        standardized_shift = (
            float((recent.mean() - reference.mean()) / reference_std)
            if reference_std > 0.0
            else float("nan")
        )
        champion_coefficient = float(
            champion_coefficients.loc[feature, "standardized_coefficient"]
        )
        challenger_coefficient = float(
            challenger_coefficients.loc[feature, "standardized_coefficient"]
        )
        feature_rows.append(
            {
                "feature": feature,
                "psi": population_stability_index(reference, recent, bins=bins),
                "reference_mean": float(reference.mean()),
                "recent_mean": float(recent.mean()),
                "standardized_mean_shift": standardized_shift,
                "champion_coefficient": champion_coefficient,
                "challenger_coefficient": challenger_coefficient,
                "champion_shift_contribution_proxy": abs(
                    standardized_shift * champion_coefficient
                ),
            }
        )
    feature_drift = pd.DataFrame(feature_rows).sort_values("psi", ascending=False)

    timeline_rows = []
    timeline_source = live.frame[["date"]].copy()
    timeline_source["champion_risk_40"] = champion_scored["risk_40"]
    timeline_source["challenger_risk_40"] = challenger_scored["risk_40"]
    months = (
        timeline_source["date"].dt.to_period("M").drop_duplicates().sort_values().tolist()
    )
    for month_period in months:
        month = month_period.to_timestamp(how="end").normalize()
        window_start = month - pd.Timedelta(days=180)
        group = timeline_source[timeline_source["date"].between(window_start, month)]
        if len(group) < 25:
            continue
        timeline_rows.append(
            {
                "month": month,
                "episodes": len(group),
                "champion_mean_risk_40": float(group["champion_risk_40"].mean()),
                "challenger_mean_risk_40": float(group["challenger_risk_40"].mean()),
                "champion_score_psi": population_stability_index(
                    champion_scored.loc[reference_mask, "risk_40"],
                    group["champion_risk_40"],
                    bins=bins,
                ),
                "challenger_score_psi": population_stability_index(
                    challenger_scored.loc[reference_mask, "risk_40"],
                    group["challenger_risk_40"],
                    bins=bins,
                ),
            }
        )
    timeline = pd.DataFrame(timeline_rows)

    champion_labeled = predict_cumulative_risk(champion, labeled.frame)
    yearly_rows = []
    for year, group in champion_labeled.groupby(champion_labeled["date"].dt.year):
        if group["target_40"].nunique() < 2:
            continue
        yearly_rows.append(
            {
                "year": int(year),
                **episode_score_summary(
                    group,
                    target_column="target_40",
                    score_column="risk_40",
                    horizon=40,
                    strata=5,
                ),
            }
        )
    yearly = pd.DataFrame(yearly_rows)

    bars = pd.read_csv(PROJECT_ROOT / base_config["modern_source"]["bars_path"])
    source_audit = (
        bars.groupby(["source", "feed", "adjustment"], dropna=False)
        .agg(rows=("ticker", "size"), first_date=("date", "min"), last_date=("date", "max"))
        .reset_index()
    )
    latest_date = pd.Timestamp(price.index.max())
    latest_members = membership.loc[latest_date].astype(bool)
    latest_coverage = float(
        price.loc[latest_date, latest_members.index[latest_members]].notna().mean()
    )
    champion_psi = population_stability_index(
        champion_scored.loc[reference_mask, "risk_40"],
        champion_scored.loc[recent_mask, "risk_40"],
        bins=bins,
    )
    challenger_psi = population_stability_index(
        challenger_scored.loc[reference_mask, "risk_40"],
        challenger_scored.loc[recent_mask, "risk_40"],
        bins=bins,
    )
    source_consistent = bool(
        len(source_audit) == 1
        and source_audit.iloc[0]["source"] == "alpaca"
        and source_audit.iloc[0]["feed"] == "sip"
        and source_audit.iloc[0]["adjustment"] == "all"
    )
    market_features = {
        "cross_sectional_dispersion_20",
        "market_breadth_20",
        "market_volatility_20",
        "market_return_20",
        "market_return_60",
    }
    top_five = feature_drift.head(5)["feature"].tolist()
    market_features_in_top_five = sum(feature in market_features for feature in top_five)
    inference = (
        "The evidence favors market-regime shift and legacy-model aging over a feed or coverage "
        "failure: the panel uses one adjusted Alpaca SIP source, latest-member coverage is "
        f"{latest_coverage:.1%}, and {market_features_in_top_five} of the five highest-PSI "
        "features are market-wide state variables."
    )

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    feature_drift.to_csv(TABLES / "v11_operational_feature_drift.csv", index=False)
    timeline.to_csv(TABLES / "v11_operational_drift_timeline.csv", index=False)
    yearly.to_csv(TABLES / "v11_champion_yearly_metrics.csv", index=False)
    source_audit.to_csv(TABLES / "v11_operational_source_audit.csv", index=False)

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].plot(
        timeline["month"], timeline["champion_score_psi"], label="Legacy champion", linewidth=2
    )
    axes[0].plot(
        timeline["month"],
        timeline["challenger_score_psi"],
        label="Modern rolling challenger",
        linewidth=2,
    )
    axes[0].axhline(0.25, color="black", linestyle="--", linewidth=1, label="Failure limit")
    axes[0].set_title("Rolling 180-day 40-day score drift")
    axes[0].set_ylabel("PSI versus 2024–2025 reference")
    axes[0].legend(frameon=False)
    top = feature_drift.head(10).sort_values("psi")
    axes[1].barh(top["feature"], top["psi"], color="#205493")
    axes[1].axvline(0.25, color="black", linestyle="--", linewidth=1)
    axes[1].set_title("Highest recent feature drift")
    axes[1].set_xlabel("PSI")
    figure.suptitle("Operational hazard-model drift forensics", fontsize=14, fontweight="bold")
    figure.tight_layout()
    figure.savefig(FIGURES / "v11_operational_drift.png", dpi=180, bbox_inches="tight")
    plt.close(figure)

    comparison = pd.read_csv(TABLES / "v11_hazard_challenger_metrics.csv")
    comparison = comparison[
        comparison["period"].eq("evaluation_2026")
        & comparison["horizon_days"].eq(40)
    ].copy()
    universe_order = ["S&P 500", "Nasdaq-100", "S&P 400"]
    model_order = ["legacy_champion", "modern_rolling"]
    colors = {"legacy_champion": "#6c757d", "modern_rolling": "#205493"}
    labels = {"legacy_champion": "Legacy champion", "modern_rolling": "Modern challenger"}
    comparison_figure, comparison_axes = plt.subplots(1, 3, figsize=(14, 4.8))
    positions = np.arange(len(universe_order))
    width = 0.36
    for offset, model_name in enumerate(model_order):
        subset = comparison[comparison["model"].eq(model_name)].set_index("universe")
        x = positions + (offset - 0.5) * width
        comparison_axes[0].bar(
            x,
            subset.loc[universe_order, "average_precision_lift"],
            width,
            label=labels[model_name],
            color=colors[model_name],
        )
        comparison_axes[1].bar(
            x,
            subset.loc[universe_order, "roc_auc"],
            width,
            color=colors[model_name],
        )
    comparison_axes[0].axhline(1.0, color="black", linestyle="--", linewidth=1)
    comparison_axes[0].set_title("40-day precision lift")
    comparison_axes[0].legend(frameon=False)
    comparison_axes[1].axhline(0.5, color="black", linestyle="--", linewidth=1)
    comparison_axes[1].set_title("40-day ROC AUC")
    for axis in comparison_axes[:2]:
        axis.set_xticks(positions, universe_order, rotation=20)
    comparison_axes[2].bar(
        ["Legacy\nchampion", "Modern\nchallenger"],
        [champion_psi, challenger_psi],
        color=[colors["legacy_champion"], colors["modern_rolling"]],
    )
    comparison_axes[2].axhline(0.25, color="black", linestyle="--", linewidth=1)
    comparison_axes[2].set_title("Current score PSI")
    comparison_figure.suptitle(
        "Modern hazard challenger: strong shadow model, promotion rule not met",
        fontsize=14,
        fontweight="bold",
    )
    comparison_figure.tight_layout()
    comparison_figure.savefig(
        FIGURES / "v11_hazard_challenger.png", dpi=180, bbox_inches="tight"
    )
    plt.close(comparison_figure)

    summary = {
        "active_champion_artifact": metadata["artifact_id"],
        "market_data_date": str(latest_date.date()),
        "latest_membership_price_coverage": latest_coverage,
        "source_consistent": source_consistent,
        "reference_episodes": int(reference_mask.sum()),
        "recent_episodes": int(recent_mask.sum()),
        "champion_score_psi": finite_or_none(champion_psi),
        "challenger_score_psi": finite_or_none(challenger_psi),
        "top_feature_drift": [
            {
                "feature": row.feature,
                "psi": finite_or_none(row.psi),
                "standardized_mean_shift": finite_or_none(row.standardized_mean_shift),
                "champion_shift_contribution_proxy": finite_or_none(
                    row.champion_shift_contribution_proxy
                ),
            }
            for row in feature_drift.head(10).itertuples(index=False)
        ],
        "inference": inference,
    }
    (TABLES / "v11_operational_drift_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
