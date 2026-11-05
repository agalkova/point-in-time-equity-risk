from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from sklearn.base import clone
from sklearn.inspection import permutation_importance

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.evaluation.calibration import (
    calibration_table,
    expected_calibration_error,
)
from risk_managed_momentum.evaluation.events import (
    thin_non_overlapping_signals,
    warning_metrics,
)
from risk_managed_momentum.evaluation.ranking import (
    classification_metrics,
    daily_rank_ic,
    decile_table,
)
from risk_managed_momentum.evaluation.walk_forward import expanding_year_folds
from risk_managed_momentum.features.advanced import build_advanced_research_dataset
from risk_managed_momentum.models.advanced import advanced_model_factories

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_v02_config() -> dict:
    with (PROJECT_ROOT / "configs" / "research_v0_2.toml").open("rb") as handle:
        return tomllib.load(handle)


def load_modern_panel(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = config["modern_source"]
    bars = pd.read_csv(source["bars_path"])
    alias_bars = pd.read_csv(source["historical_alias_bars_path"])
    bars = pd.concat([bars, alias_bars[bars.columns]], ignore_index=True)
    membership = pd.read_csv(source["membership_path"])
    with Path(source["aliases_path"]).open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    return build_point_in_time_panel(bars, membership, aliases)


def summarize(
    frame: pd.DataFrame,
    score_column: str,
    *,
    is_probability: bool = True,
) -> dict[str, float | int | None]:
    metrics = classification_metrics(frame["target"], frame[score_column].to_numpy())
    rank_ic = daily_rank_ic(frame, score_column)
    deciles = decile_table(frame, score_column)
    calibration = (
        calibration_table(frame["target"], frame[score_column])
        if is_probability
        else None
    )
    bottom = float(deciles.loc[deciles["risk_decile"] == 1, "event_rate"].iloc[0])
    top = float(deciles.loc[deciles["risk_decile"] == 10, "event_rate"].iloc[0])
    result = {
        **metrics,
        "mean_daily_rank_ic": float(rank_ic.mean()),
        "top_decile_event_rate": top,
        "bottom_decile_event_rate": bottom,
        "top_minus_bottom_event_rate": top - bottom,
        "expected_calibration_error": (
            expected_calibration_error(calibration) if calibration is not None else None
        ),
    }
    if not is_probability:
        result["brier_score"] = None
    return result


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    config = load_v02_config()

    legacy_price, legacy_volume = load_legacy_wide(
        base_config["legacy_source"]["price_path"],
        base_config["legacy_source"]["volume_path"],
    )
    legacy = build_advanced_research_dataset(legacy_price, legacy_volume, base_config)
    legacy_frame = legacy.frame.copy()
    legacy_frame["dataset_source"] = "legacy"

    modern_price, modern_volume, membership = load_modern_panel(base_config)
    modern = build_advanced_research_dataset(
        modern_price, modern_volume, base_config, membership=membership
    )
    modern_frame = modern.frame.copy()
    modern_frame["dataset_source"] = "modern"
    if legacy.feature_columns != modern.feature_columns:
        raise RuntimeError("Advanced legacy and modern feature schemas differ")

    combined = pd.concat([legacy_frame, modern_frame], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"]).dt.normalize()
    validation = config["validation"]
    folds = expanding_year_folds(
        combined["date"],
        first_test_year=int(validation["first_test_year"]),
        last_test_year=int(validation["last_test_year"]),
        purge_trading_days=int(validation["purge_trading_days"]),
    )
    factories = advanced_model_factories(config)
    outputs = []
    fold_rows = []
    last_models = {}
    last_test = None
    for fold in folds:
        train = combined[combined["date"].isin(fold.train_dates)].copy()
        test = combined[
            combined["date"].isin(fold.test_dates) & combined["dataset_source"].eq("modern")
        ].copy()
        if len(train) < int(validation["minimum_training_observations"]) or test.empty:
            continue
        prediction_columns = {}
        for name, prototype in factories.items():
            model = clone(prototype).fit(train[legacy.feature_columns], train["target"])
            column = f"score_{name}"
            test[column] = model.predict_proba(test[legacy.feature_columns])[:, 1]
            prediction_columns[name] = column
            metrics = summarize(test, column)
            fold_rows.append(
                {
                    "test_year": fold.test_year,
                    "model": name,
                    "training_observations": len(train),
                    "test_observations": len(test),
                    **metrics,
                }
            )
            last_models[name] = model

        weights = config["ensemble"]
        test["score_ensemble"] = (
            float(weights["logistic_weight"]) * test[prediction_columns["logistic"]]
            + float(weights["hist_gradient_boosting_weight"])
            * test[prediction_columns["hist_gradient_boosting"]]
        )
        test["score_fixed_composite"] = test[
            [
                "rank_ret_60",
                "rank_volatility_20",
                "rank_beta_60",
                "rank_idiosyncratic_volatility_60",
            ]
        ].mean(axis=1)
        for name in ["ensemble", "fixed_composite"]:
            metrics = summarize(
                test,
                f"score_{name}",
                is_probability=name != "fixed_composite",
            )
            fold_rows.append(
                {
                    "test_year": fold.test_year,
                    "model": name,
                    "training_observations": len(train),
                    "test_observations": len(test),
                    **metrics,
                }
            )
        outputs.append(test)
        last_test = test

    if not outputs or last_test is None:
        raise RuntimeError("No walk-forward folds were produced")
    oof = pd.concat(outputs, ignore_index=True).sort_values(["date", "ticker"])
    score_columns = {
        "logistic": "score_logistic",
        "hist_gradient_boosting": "score_hist_gradient_boosting",
        "ensemble": "score_ensemble",
        "fixed_composite": "score_fixed_composite",
    }
    pooled = {
        name: summarize(oof, column, is_probability=name != "fixed_composite")
        for name, column in score_columns.items()
    }

    warning_percentile = float(config["events"]["warning_percentile"])
    for name, column in score_columns.items():
        cutoff = oof.groupby("date")[column].transform(
            lambda values: values.quantile(warning_percentile)
        )
        oof[f"warning_{name}"] = oof[column] >= cutoff
    thinned = thin_non_overlapping_signals(
        oof,
        horizon_days=int(config["events"]["non_overlap_days"]),
    )
    event_results = {}
    for name, column in score_columns.items():
        event_classification = classification_metrics(
            thinned["target"], thinned[column].to_numpy()
        )
        if name == "fixed_composite":
            event_classification["brier_score"] = None
        event_results[name] = {
            "classification": event_classification,
            "warnings": warning_metrics(
                thinned,
                score_column=column,
                warning_percentile=warning_percentile,
                warning_column=f"warning_{name}",
            ),
        }

    importance_sample = last_test.sample(
        min(10000, len(last_test)),
        random_state=int(config["project"]["random_seed"]),
    )
    permutation = permutation_importance(
        last_models["hist_gradient_boosting"],
        importance_sample[legacy.feature_columns],
        importance_sample["target"],
        scoring="average_precision",
        n_repeats=3,
        random_state=int(config["project"]["random_seed"]),
        n_jobs=1,
    )
    importance = pd.DataFrame(
        {
            "feature": legacy.feature_columns,
            "mean_average_precision_decrease": permutation.importances_mean,
            "standard_deviation": permutation.importances_std,
        }
    ).sort_values("mean_average_precision_decrease", ascending=False)

    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": "exploratory; the modern period was already opened under v0.1",
        "folds": [fold.test_year for fold in folds],
        "feature_count": len(legacy.feature_columns),
        "out_of_fold_observations": len(oof),
        "non_overlapping_event_observations": len(thinned),
        "pooled_scores": pooled,
        "event_results": event_results,
    }
    output_dir = PROJECT_ROOT / "reports" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(output_dir / "v02_walk_forward_folds.csv", index=False)
    importance.to_csv(output_dir / "v02_boosting_permutation_importance.csv", index=False)
    oof[
        [
            "date", "ticker", "target", "first_breach_days", "drawdown_severity",
            "rank_ret_60",
            *score_columns.values(),
        ]
    ].to_csv(output_dir / "v02_out_of_fold_predictions.csv.gz", index=False, compression="gzip")
    (output_dir / "v02_walk_forward_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
