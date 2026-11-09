from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.integrity_panel import load_integrity_corrected_sp500
from risk_managed_momentum.evaluation.hazard import episode_score_summary
from risk_managed_momentum.evaluation.paired_bootstrap import paired_date_block_bootstrap
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import (
    FittedHazardModel,
    fit_hazard_model,
    predict_cumulative_risk,
    standardized_coefficients,
)
from risk_managed_momentum.operations.registry import load_active_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def fit_candidate(
    episodes: pd.DataFrame,
    feature_columns: list[str],
    hazard: dict[str, Any],
    config: dict[str, Any],
    *,
    start: str,
) -> tuple[FittedHazardModel, pd.DataFrame]:
    training = episodes[episodes["date"].between(start, config["model"]["training_end"])]
    model = fit_hazard_model(
        training,
        feature_columns,
        hazard["outcome"]["horizon_end_days"],
        c=float(config["model"]["c"]),
        maximum_iterations=int(config["model"]["maximum_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )
    return model, training


def score_model(
    model: FittedHazardModel,
    frame: pd.DataFrame,
    *,
    model_name: str,
    period: str,
    strata: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    scored = predict_cumulative_risk(model, frame)
    rows = []
    for horizon in model.horizons:
        rows.append(
            {
                "model": model_name,
                "period": period,
                **episode_score_summary(
                    scored,
                    target_column=f"target_{horizon}",
                    score_column=f"risk_{horizon}",
                    horizon=horizon,
                    strata=strata,
                ),
            }
        )
    return scored, pd.DataFrame(rows)


def main() -> None:
    base = load_config(PROJECT_ROOT / "configs/research.toml")
    hazard = load_toml(PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml")
    config = load_toml(PROJECT_ROOT / "configs/research_v1_2_integrity_expansion.toml")
    price, volume, membership, resolution = load_integrity_corrected_sp500(
        PROJECT_ROOT, base, config
    )
    dataset = build_exuberance_episode_dataset(
        price,
        volume,
        base,
        hazard,
        membership=membership,
        outcome_price=resolution.prices,
    )
    episodes = dataset.frame

    starts = {
        "expanded_2016": config["model"]["expanded_start"],
        "modern_2020": config["model"]["modern_start"],
        "rolling_2022": config["model"]["rolling_start"],
    }
    candidates: dict[str, FittedHazardModel] = {}
    training_rows = []
    validation = episodes[
        episodes["date"].between(
            config["model"]["selection_start"], config["model"]["selection_end"]
        )
    ]
    validation_metrics = []
    strata = int(config["inference"]["risk_strata"])
    for name, start in starts.items():
        model, training = fit_candidate(
            episodes, dataset.feature_columns, hazard, config, start=start
        )
        candidates[name] = model
        training_rows.append(
            {
                "model": name,
                "training_start": str(training["date"].min().date()),
                "training_end": str(training["date"].max().date()),
                "episodes": len(training),
                "events_60": int(training["target_60"].sum()),
            }
        )
        _, metrics = score_model(
            model,
            validation,
            model_name=name,
            period="selection_2025",
            strata=strata,
        )
        validation_metrics.append(metrics)

    validation_table = pd.concat(validation_metrics, ignore_index=True)
    horizon = int(config["model"]["selection_horizon_days"])
    selection = validation_table[validation_table["horizon_days"].eq(horizon)].sort_values(
        [
            config["model"]["selection_primary_metric"],
            config["model"]["selection_tiebreaker"],
        ],
        ascending=False,
    )
    selected_name = str(selection.iloc[0]["model"])
    selected = candidates[selected_name]

    evaluation = episodes[
        episodes["date"].between(
            config["model"]["evaluation_start"], config["model"]["evaluation_end"]
        )
    ]
    champion, champion_metadata, _ = load_active_model(
        PROJECT_ROOT / "reports/operations/model_registry"
    )
    if champion.feature_columns != dataset.feature_columns:
        raise RuntimeError("Active champion and integrity study use different feature schemas")
    champion_scored, champion_metrics = score_model(
        champion,
        evaluation,
        model_name="active_champion",
        period="evaluation_2026",
        strata=strata,
    )
    selected_scored, selected_metrics = score_model(
        selected,
        evaluation,
        model_name=selected_name,
        period="evaluation_2026",
        strata=strata,
    )
    predictions = evaluation[["episode_id", "date", "ticker", f"target_{horizon}"]].copy()
    predictions["champion_risk_40"] = champion_scored[f"risk_{horizon}"].to_numpy()
    predictions["challenger_risk_40"] = selected_scored[f"risk_{horizon}"].to_numpy()
    bootstrap = paired_date_block_bootstrap(
        predictions,
        target_column=f"target_{horizon}",
        first_score_column="champion_risk_40",
        second_score_column="challenger_risk_40",
        block_length=int(config["inference"]["paired_block_bootstrap_days"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )

    all_metrics = pd.concat(
        [validation_table, champion_metrics, selected_metrics], ignore_index=True
    )
    TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(training_rows).to_csv(TABLES / "v12_training_audit.csv", index=False)
    all_metrics.to_csv(TABLES / "v12_hazard_metrics.csv", index=False)
    predictions.to_csv(TABLES / "v12_paired_predictions.csv", index=False)
    bootstrap.to_csv(TABLES / "v12_paired_bootstrap.csv", index=False)
    standardized_coefficients(selected).to_csv(
        TABLES / "v12_selected_coefficients.csv", index=False
    )

    primary = all_metrics[
        (all_metrics["period"] == "evaluation_2026") & all_metrics["horizon_days"].eq(horizon)
    ].set_index("model")
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": config["project"]["claim_status"],
        "selected_model": selected_name,
        "selected_on": "2025 average-precision lift at 40 trading days",
        "selection_episodes": len(validation),
        "evaluation_episodes": len(evaluation),
        "evaluation_last_mature_onset": str(evaluation["date"].max().date()),
        "active_champion_artifact_id": champion_metadata["artifact_id"],
        "active_champion": primary.loc["active_champion"].to_dict(),
        "selected_challenger": primary.loc[selected_name].to_dict(),
        "paired_bootstrap": bootstrap.to_dict(orient="records"),
        "promotion_decision": "research_only_no_promotion",
        "promotion_reason": (
            "The 2026 interval was previously opened and cannot provide untouched evidence."
        ),
    }
    (TABLES / "v12_hazard_summary.json").write_text(
        json.dumps(json_safe(summary), indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(json_safe(summary), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
