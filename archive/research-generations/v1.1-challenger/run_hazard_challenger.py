from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.universes import (
    load_ndx_panel,
    load_sp400_panel,
    load_sp500_panel,
)
from risk_managed_momentum.evaluation.hazard import episode_score_summary
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import (
    FittedHazardModel,
    fit_hazard_model,
    predict_cumulative_risk,
)
from risk_managed_momentum.operations.monitoring import file_sha256, population_stability_index
from risk_managed_momentum.operations.registry import (
    canonical_json_bytes,
    load_active_model,
    register_model_artifact,
    set_model_pointer,
)
from risk_managed_momentum.prospective import content_digest

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
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def fit_candidate(
    episodes: pd.DataFrame,
    feature_columns: list[str],
    hazard_config: dict[str, Any],
    challenger_config: dict[str, Any],
    *,
    start: str,
    end: str,
) -> tuple[FittedHazardModel, pd.DataFrame]:
    training = episodes[episodes["date"].between(start, end)].copy()
    model = fit_hazard_model(
        training,
        feature_columns,
        hazard_config["outcome"]["horizon_end_days"],
        c=float(challenger_config["model"]["c"]),
        maximum_iterations=int(challenger_config["model"]["maximum_iterations"]),
        random_seed=int(challenger_config["project"]["random_seed"]),
    )
    return model, training


def score_metrics(
    model: FittedHazardModel,
    episodes: pd.DataFrame,
    *,
    universe: str,
    period: str,
    model_name: str,
    strata: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    scored = predict_cumulative_risk(model, episodes)
    rows = []
    for horizon in model.horizons:
        rows.append(
            {
                "universe": universe,
                "period": period,
                "model": model_name,
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
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    hazard_config = load_toml(
        PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml"
    )
    config = load_toml(PROJECT_ROOT / "configs/research_v1_1_hazard_challenger.toml")
    registry = PROJECT_ROOT / "reports/operations/model_registry"
    champion, champion_metadata, _ = load_active_model(registry)
    price, volume, membership = load_sp500_panel(PROJECT_ROOT, base_config)
    episodes = build_exuberance_episode_dataset(
        price,
        volume,
        base_config,
        hazard_config,
        membership=membership,
    )
    if episodes.feature_columns != champion.feature_columns:
        raise RuntimeError("Modern feature schema differs from active champion")

    candidates: dict[str, FittedHazardModel] = {}
    training_audit: dict[str, Any] = {}
    expanding, expanding_training = fit_candidate(
        episodes.frame,
        episodes.feature_columns,
        hazard_config,
        config,
        start=config["data"]["training_start"],
        end=config["data"]["expanding_training_end"],
    )
    candidates["modern_expanding"] = expanding
    training_audit["modern_expanding"] = {
        "start": str(expanding_training["date"].min().date()),
        "end": str(expanding_training["date"].max().date()),
        "episodes": len(expanding_training),
        "events_60": int(expanding_training["target_60"].sum()),
    }
    rolling, rolling_training = fit_candidate(
        episodes.frame,
        episodes.feature_columns,
        hazard_config,
        config,
        start=config["data"]["rolling_training_start"],
        end=config["data"]["expanding_training_end"],
    )
    candidates["modern_rolling"] = rolling
    training_audit["modern_rolling"] = {
        "start": str(rolling_training["date"].min().date()),
        "end": str(rolling_training["date"].max().date()),
        "episodes": len(rolling_training),
        "events_60": int(rolling_training["target_60"].sum()),
    }

    validation = episodes.frame[
        episodes.frame["date"].between(
            config["data"]["validation_start"], config["data"]["validation_end"]
        )
    ].copy()
    validation_metrics = []
    for name, model in candidates.items():
        _, metrics = score_metrics(
            model,
            validation,
            universe="S&P 500",
            period="validation_2025",
            model_name=name,
            strata=int(config["evaluation"]["risk_strata"]),
        )
        validation_metrics.append(metrics)
    validation_table = pd.concat(validation_metrics, ignore_index=True)
    selection_horizon = int(config["model"]["selection_horizon_days"])
    selection = validation_table[validation_table["horizon_days"].eq(selection_horizon)]
    selection = selection.sort_values(
        [
            config["model"]["selection_primary_metric"],
            config["model"]["selection_tiebreaker"],
        ],
        ascending=False,
    )
    selected_name = str(selection.iloc[0]["model"])
    selected = candidates[selected_name]

    loaders = {
        "S&P 500": lambda: (price, volume, membership),
        "Nasdaq-100": lambda: load_ndx_panel(PROJECT_ROOT),
        "S&P 400": lambda: load_sp400_panel(PROJECT_ROOT),
    }
    all_metrics = [validation_table]
    prediction_frames = []
    primary_by_universe: dict[str, dict[str, Any]] = {}
    for universe, loader in loaders.items():
        universe_price, universe_volume, universe_membership = loader()
        universe_episodes = build_exuberance_episode_dataset(
            universe_price,
            universe_volume,
            base_config,
            hazard_config,
            membership=universe_membership,
        )
        evaluation = universe_episodes.frame[
            universe_episodes.frame["date"].between(
                config["data"]["evaluation_start"],
                config["data"]["evaluation_end"],
            )
        ].copy()
        champion_scored, champion_metrics = score_metrics(
            champion,
            evaluation,
            universe=universe,
            period="evaluation_2026",
            model_name="legacy_champion",
            strata=int(config["evaluation"]["risk_strata"]),
        )
        challenger_scored, challenger_metrics = score_metrics(
            selected,
            evaluation,
            universe=universe,
            period="evaluation_2026",
            model_name=selected_name,
            strata=int(config["evaluation"]["risk_strata"]),
        )
        all_metrics.extend([champion_metrics, challenger_metrics])
        prediction = evaluation[["episode_id", "date", "ticker", "target_40"]].copy()
        prediction["universe"] = universe
        prediction["champion_risk_40"] = champion_scored["risk_40"].to_numpy()
        prediction["challenger_risk_40"] = challenger_scored["risk_40"].to_numpy()
        prediction_frames.append(prediction)
        horizon = pd.concat([champion_metrics, challenger_metrics])
        horizon = horizon[horizon["horizon_days"].eq(selection_horizon)].set_index("model")
        primary_by_universe[universe] = {
            "champion": horizon.loc["legacy_champion"].to_dict(),
            "challenger": horizon.loc[selected_name].to_dict(),
        }

    live = build_exuberance_episode_dataset(
        price,
        volume,
        base_config,
        hazard_config,
        membership=membership,
        include_unlabeled=True,
    )
    champion_live = predict_cumulative_risk(champion, live.frame)
    challenger_live = predict_cumulative_risk(selected, live.frame)
    reference_mask = live.frame["date"].between(
        config["drift"]["reference_start"], config["drift"]["reference_end"]
    )
    recent_cutoff = pd.Timestamp(price.index.max()) - pd.Timedelta(
        days=int(config["drift"]["recent_calendar_days"])
    )
    recent_mask = live.frame["date"].ge(recent_cutoff)
    champion_psi = population_stability_index(
        champion_live.loc[reference_mask, "risk_40"],
        champion_live.loc[recent_mask, "risk_40"],
        bins=int(config["drift"]["bins"]),
    )
    challenger_psi = population_stability_index(
        challenger_live.loc[reference_mask, "risk_40"],
        challenger_live.loc[recent_mask, "risk_40"],
        bins=int(config["drift"]["bins"]),
    )

    rules = config["promotion"]
    sp500 = primary_by_universe["S&P 500"]
    champion_primary = sp500["champion"]
    challenger_primary = sp500["challenger"]
    sp500_checks = {
        "roc_auc_floor": challenger_primary["roc_auc"]
        >= float(rules["minimum_challenger_roc_auc"]),
        "roc_auc_not_materially_worse": challenger_primary["roc_auc"]
        >= champion_primary["roc_auc"]
        - float(rules["maximum_roc_auc_decline_vs_champion"]),
        "precision_lift_floor": challenger_primary["average_precision_lift"]
        >= float(rules["minimum_average_precision_lift"]),
        "precision_lift_improvement": challenger_primary["average_precision_lift"]
        >= champion_primary["average_precision_lift"]
        + float(rules["minimum_lift_improvement_vs_champion"]),
        "brier_not_materially_worse": challenger_primary["brier_score"]
        <= champion_primary["brier_score"]
        + float(rules["maximum_brier_increase_vs_champion"]),
        "current_score_psi": challenger_psi <= float(rules["maximum_current_score_psi"]),
    }
    transfer_checks = {}
    for universe in ["Nasdaq-100", "S&P 400"]:
        metrics = primary_by_universe[universe]["challenger"]
        transfer_checks[universe] = {
            "roc_auc_floor": metrics["roc_auc"]
            >= float(rules["minimum_challenger_roc_auc"]),
            "precision_lift_floor": metrics["average_precision_lift"]
            >= float(rules["minimum_average_precision_lift"]),
        }
        transfer_checks[universe]["passed"] = all(transfer_checks[universe].values())
    transfer_passes = sum(item["passed"] for item in transfer_checks.values())
    promotion_passed = all(sp500_checks.values()) and transfer_passes >= int(
        rules["minimum_transfer_universes_passing"]
    )

    source = base_config["modern_source"]
    training_paths = [
        PROJECT_ROOT / source["bars_path"],
        PROJECT_ROOT / source["membership_path"],
        PROJECT_ROOT / source["aliases_path"],
    ]
    training_hashes = {
        str(path.relative_to(PROJECT_ROOT)): file_sha256(path) for path in training_paths
    }
    config_paths = [
        PROJECT_ROOT / "configs/research.toml",
        PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml",
        PROJECT_ROOT / "configs/research_v1_1_hazard_challenger.toml",
    ]
    config_hashes = {
        str(path.relative_to(PROJECT_ROOT)): file_sha256(path) for path in config_paths
    }
    training_data_digest = content_digest(canonical_json_bytes(training_hashes))
    training_config_digest = content_digest(canonical_json_bytes(config_hashes))
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    shadow_path, shadow_reused = register_model_artifact(
        registry,
        selected,
        {
            "model_specification": (
                f"{config['project']['specification_version']}-{selected_name}"
            ),
            "training_data_sha256": training_data_digest,
            "training_source_sha256": training_hashes,
            "training_config_sha256": training_config_digest,
            "training_config_files_sha256": config_hashes,
            "training_first_episode_date": training_audit[selected_name]["start"],
            "training_last_episode_date": training_audit[selected_name]["end"],
            "training_episodes": training_audit[selected_name]["episodes"],
            "training_events_60": training_audit[selected_name]["events_60"],
            "registered_from_code_revision": revision,
            "release_stage": "shadow",
        },
    )
    set_model_pointer(registry, shadow_path.name, "SHADOW")

    metrics_table = pd.concat(all_metrics, ignore_index=True)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": config["project"]["claim_status"],
        "active_champion_artifact": champion_metadata["artifact_id"],
        "training": training_audit,
        "validation_episodes": len(validation),
        "selected_challenger": selected_name,
        "shadow_artifact_id": shadow_path.name,
        "shadow_registration_reused": shadow_reused,
        "primary_40_day_results": primary_by_universe,
        "operational_score_psi": {
            "legacy_champion": champion_psi,
            selected_name: challenger_psi,
        },
        "promotion": {
            "sp500_checks": sp500_checks,
            "transfer_checks": transfer_checks,
            "transfer_universes_passing": transfer_passes,
            "passed": promotion_passed,
            "action": "eligible_for_review" if promotion_passed else "remain_shadow_only",
        },
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    validation_table.to_csv(TABLES / "v11_hazard_challenger_validation.csv", index=False)
    metrics_table.to_csv(TABLES / "v11_hazard_challenger_metrics.csv", index=False)
    predictions.to_csv(
        TABLES / "v11_hazard_challenger_predictions.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    safe_summary = json_safe(summary)
    (TABLES / "v11_hazard_challenger_summary.json").write_text(
        json.dumps(safe_summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(json.dumps(safe_summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
