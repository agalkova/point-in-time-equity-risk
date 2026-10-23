from __future__ import annotations

import json
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.evaluation.hazard import (
    calibration_by_stratum,
    episode_score_summary,
)
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import (
    fit_hazard_model,
    predict_cumulative_risk,
    standardized_coefficients,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"
FIGURES = PROJECT_ROOT / "docs/figures"


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_modern_sp500(base_config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = base_config["modern_source"]
    bars = pd.read_csv(PROJECT_ROOT / source["bars_path"])
    aliases_bars = pd.read_csv(PROJECT_ROOT / source["historical_alias_bars_path"])
    bars = pd.concat([bars, aliases_bars[bars.columns]], ignore_index=True)
    membership = pd.read_csv(PROJECT_ROOT / source["membership_path"])
    aliases = load_toml(PROJECT_ROOT / source["aliases_path"])["alias"]
    return build_point_in_time_panel(bars, membership, aliases)


def load_ndx() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = load_toml(PROJECT_ROOT / "configs/research_v0_7_ndx.toml")
    bars = pd.read_csv(PROJECT_ROOT / config["data"]["bars_path"])
    membership = pd.read_csv(PROJECT_ROOT / config["data"]["membership_path"])
    aliases = load_toml(PROJECT_ROOT / "data/reference/ndx_symbol_aliases.toml")["alias"]
    return build_point_in_time_panel(bars, membership, aliases)


def load_sp400() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = load_toml(PROJECT_ROOT / "configs/research_v0_8_sp400.toml")
    bars = pd.read_csv(PROJECT_ROOT / config["data"]["bars_path"])
    gap_path = PROJECT_ROOT / config["data"]["historical_gap_bars_path"]
    if gap_path.exists():
        gap_bars = pd.read_csv(gap_path)
        bars = pd.concat([bars, gap_bars[bars.columns]], ignore_index=True)
    membership = pd.read_csv(PROJECT_ROOT / config["data"]["membership_path"])
    aliases = load_toml(PROJECT_ROOT / "data/reference/sp400_symbol_aliases.toml")["alias"]
    return build_point_in_time_panel(bars, membership, aliases)


def benchmark_summary(frame: pd.DataFrame, target_column: str) -> dict[str, float]:
    target = frame[target_column]
    score = frame["rank_ret_60"]
    prevalence = float(target.mean())
    average_precision = float(average_precision_score(target, score))
    return {
        "roc_auc": float(roc_auc_score(target, score)),
        "average_precision": average_precision,
        "average_precision_lift": average_precision / prevalence,
    }


def make_figure(metrics: pd.DataFrame, calibration: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    colors = {"S&P 500": "#205493", "Nasdaq-100": "#2ca25f", "S&P 400": "#d95f0e"}
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for universe, group in metrics.groupby("universe"):
        axes[0].plot(
            group["horizon_days"],
            group["average_precision_lift"],
            marker="o",
            linewidth=2,
            label=universe,
            color=colors[universe],
        )
    axes[0].axhline(1.0, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("Precision lift across forecast horizons")
    axes[0].set_xlabel("Horizon (trading days)")
    axes[0].set_ylabel("Average precision / prevalence")
    axes[0].legend(frameon=False)

    horizon_40 = calibration[calibration["horizon_days"].eq(40)]
    for universe, group in horizon_40.groupby("universe"):
        axes[1].plot(
            group["risk_stratum"],
            group["observed_event_rate"],
            marker="o",
            linewidth=2,
            label=universe,
            color=colors[universe],
        )
    axes[1].set_title("Observed 40-day drawdown risk")
    axes[1].set_xlabel("Model risk quintile")
    axes[1].set_ylabel("Event rate")
    axes[1].set_xticks(range(1, 6))
    axes[1].legend(frameon=False)
    figure.suptitle("Exuberance episode hazard model", fontsize=14, fontweight="bold")
    figure.tight_layout()
    figure.savefig(FIGURES / "v09_exuberance_hazard.png", dpi=180, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    config = load_toml(PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml")
    legacy_price, legacy_volume = load_legacy_wide(
        PROJECT_ROOT / base_config["legacy_source"]["price_path"],
        PROJECT_ROOT / base_config["legacy_source"]["volume_path"],
    )
    legacy = build_exuberance_episode_dataset(
        legacy_price, legacy_volume, base_config, config
    )
    training = legacy.frame[legacy.frame["date"].between(
        config["training"]["start"], config["training"]["end"]
    )].copy()
    model = fit_hazard_model(
        training,
        legacy.feature_columns,
        config["outcome"]["horizon_end_days"],
        c=float(config["model"]["c"]),
        maximum_iterations=int(config["model"]["maximum_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )

    loaders = {
        "S&P 500": lambda: load_modern_sp500(base_config),
        "Nasdaq-100": load_ndx,
        "S&P 400": load_sp400,
    }
    scored_frames = []
    metric_rows = []
    calibration_rows = []
    universe_summaries = {}
    for universe, loader in loaders.items():
        price, volume, membership = loader()
        episodes = build_exuberance_episode_dataset(
            price, volume, base_config, config, membership=membership
        )
        if episodes.feature_columns != legacy.feature_columns:
            raise RuntimeError(f"Feature schema mismatch for {universe}")
        evaluation = episodes.frame[episodes.frame["date"].between(
            config["evaluation"]["start"], config["evaluation"]["end"]
        )].copy()
        scored = predict_cumulative_risk(model, evaluation)
        scored["universe"] = universe
        scored_frames.append(scored)
        universe_summaries[universe] = {
            "episodes": len(scored),
            "first_episode": str(scored["date"].min().date()),
            "last_episode_with_full_60_day_outcome": str(scored["date"].max().date()),
        }
        for horizon in model.horizons:
            summary = episode_score_summary(
                scored,
                target_column=f"target_{horizon}",
                score_column=f"risk_{horizon}",
                horizon=horizon,
                strata=int(config["evaluation"]["risk_strata"]),
            )
            benchmark = benchmark_summary(scored, f"target_{horizon}")
            metric_rows.append(
                {
                    "universe": universe,
                    **summary,
                    "benchmark_roc_auc": benchmark["roc_auc"],
                    "benchmark_average_precision_lift": benchmark["average_precision_lift"],
                }
            )
            calibration_rows.append(
                calibration_by_stratum(
                    scored,
                    universe=universe,
                    horizon=horizon,
                    score_column=f"risk_{horizon}",
                    target_column=f"target_{horizon}",
                    strata=int(config["evaluation"]["risk_strata"]),
                )
            )

    metrics = pd.DataFrame(metric_rows)
    calibration = pd.concat(calibration_rows, ignore_index=True)
    coefficients = standardized_coefficients(model)
    predictions = pd.concat(scored_frames, ignore_index=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(TABLES / "v09_exuberance_hazard_metrics.csv", index=False)
    calibration.to_csv(TABLES / "v09_exuberance_hazard_calibration.csv", index=False)
    coefficients.to_csv(TABLES / "v09_exuberance_hazard_coefficients.csv", index=False)
    prediction_columns = [
        "universe", "episode_id", "date", "ticker", "first_breach_days",
        "future_min_return_60", "rank_ret_60",
        *[f"target_{horizon}" for horizon in model.horizons],
        *[f"risk_{horizon}" for horizon in model.horizons],
    ]
    predictions[prediction_columns].to_csv(
        TABLES / "v09_exuberance_hazard_predictions.csv.gz",
        index=False,
        compression="gzip",
    )
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": config["project"]["claim_status"],
        "training_episodes": len(training),
        "training_events_by_60_days": int(training["target_60"].sum()),
        "features": len(legacy.feature_columns),
        "horizons": model.horizons,
        "universes": universe_summaries,
        "primary_40_day_results": {
            row["universe"]: {
                key: row[key]
                for key in [
                    "episodes", "events", "prevalence", "roc_auc",
                    "average_precision_lift", "brier_score",
                    "top_to_bottom_risk_ratio",
                    "median_lead_time_days_top_stratum_events",
                    "benchmark_roc_auc", "benchmark_average_precision_lift",
                ]
            }
            for row in metrics[metrics["horizon_days"].eq(40)].to_dict("records")
        },
    }
    (TABLES / "v09_exuberance_hazard_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    make_figure(metrics, calibration)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

