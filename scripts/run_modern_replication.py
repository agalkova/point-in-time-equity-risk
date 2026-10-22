from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from sklearn.base import clone

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.panel import build_point_in_time_panel, coverage_summary
from risk_managed_momentum.evaluation.ranking import (
    add_daily_deciles,
    classification_metrics,
    daily_rank_ic,
    decile_table,
    moving_block_interval,
)
from risk_managed_momentum.features.build import build_research_dataset, split_research_dataset
from risk_managed_momentum.models.drawdown import select_logistic_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_aliases(path: Path) -> list[dict[str, object]]:
    with path.open("rb") as handle:
        return tomllib.load(handle)["alias"]


def daily_event_spread(frame: pd.DataFrame, score_column: str) -> pd.Series:
    work = frame[["date", "target", score_column]].copy()
    work["risk_decile"] = add_daily_deciles(work, score_column)
    rates = work.dropna(subset=["risk_decile"]).groupby(["date", "risk_decile"])[
        "target"
    ].mean().unstack()
    return rates.get(10.0, pd.Series(index=rates.index, dtype=float)).sub(
        rates.get(1.0, pd.Series(index=rates.index, dtype=float))
    ).dropna()


def score_summary(frame: pd.DataFrame, score_column: str, config: dict) -> dict[str, object]:
    metrics = classification_metrics(frame["target"], frame[score_column].to_numpy())
    deciles = decile_table(frame, score_column)
    rank_ic = daily_rank_ic(frame, score_column)
    spread = daily_event_spread(frame, score_column)
    block = int(config["inference"]["block_bootstrap_days"])
    iterations = int(config["inference"]["bootstrap_iterations"])
    seed = int(config["project"]["random_seed"])
    bottom = float(deciles.loc[deciles["risk_decile"] == 1, "event_rate"].iloc[0])
    top = float(deciles.loc[deciles["risk_decile"] == 10, "event_rate"].iloc[0])
    return {
        **metrics,
        "mean_daily_rank_ic": float(rank_ic.mean()),
        "mean_daily_rank_ic_95pct_block_interval": list(
            moving_block_interval(
                rank_ic, block_length=block, iterations=iterations, random_seed=seed
            )
        ),
        "top_decile_event_rate": top,
        "bottom_decile_event_rate": bottom,
        "top_minus_bottom_event_rate": top - bottom,
        "top_to_bottom_risk_ratio": top / bottom if bottom else float("nan"),
        "mean_daily_event_spread": float(spread.mean()),
        "mean_daily_event_spread_95pct_block_interval": list(
            moving_block_interval(
                spread, block_length=block, iterations=iterations, random_seed=seed
            )
        ),
    }


def main() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")

    legacy_price, legacy_volume = load_legacy_wide(
        config["legacy_source"]["price_path"],
        config["legacy_source"]["volume_path"],
    )
    legacy_dataset = build_research_dataset(legacy_price, legacy_volume, config)
    legacy_splits = split_research_dataset(legacy_dataset, config)
    selected = select_logistic_model(
        legacy_splits["train"],
        legacy_splits["validation"],
        legacy_dataset.feature_columns,
        random_seed=int(config["project"]["random_seed"]),
    )
    development = pd.concat(legacy_splits.values(), ignore_index=True)
    final_model = clone(selected.model).fit(
        development[legacy_dataset.feature_columns], development["target"]
    )

    source = config["modern_source"]
    bars = pd.read_csv(project_path(source["bars_path"]))
    alias_bars = pd.read_csv(project_path(source["historical_alias_bars_path"]))
    bars = pd.concat([bars, alias_bars[bars.columns]], ignore_index=True)
    membership_long = pd.read_csv(project_path(source["membership_path"]))
    aliases = load_aliases(project_path(source["aliases_path"]))
    price, volume, membership = build_point_in_time_panel(bars, membership_long, aliases)
    coverage = coverage_summary(price, membership)

    modern_dataset = build_research_dataset(price, volume, config, membership=membership)
    split = config["splits"]["modern_holdout"]
    modern = modern_dataset.frame[
        modern_dataset.frame["date"].between(split["start"], split["end"])
    ].copy()
    if modern.empty:
        raise RuntimeError("Modern holdout contains no eligible observations")
    if modern_dataset.feature_columns != legacy_dataset.feature_columns:
        raise RuntimeError("Legacy and modern feature schemas differ")

    modern["risk_score"] = final_model.predict_proba(
        modern[modern_dataset.feature_columns]
    )[:, 1]
    baseline_columns = {
        "model": "risk_score",
        "return_60": "rank_ret_60",
        "volatility_20": "rank_volatility_20",
        "beta_60": "rank_beta_60",
        "idiosyncratic_volatility_60": "rank_idiosyncratic_volatility_60",
    }
    modern["fixed_rank_composite"] = modern[
        [
            "rank_ret_60",
            "rank_volatility_20",
            "rank_beta_60",
            "rank_idiosyncratic_volatility_60",
        ]
    ].mean(axis=1)
    baseline_columns["fixed_rank_composite"] = "fixed_rank_composite"
    comparisons = {
        name: score_summary(modern, column, config)
        for name, column in baseline_columns.items()
    }

    annual_rows = []
    for year, group in modern.groupby(modern["date"].dt.year):
        yearly = score_summary(group, "risk_score", config)
        annual_rows.append(
            {
                "year": int(year),
                "observations": yearly["observations"],
                "prevalence": yearly["prevalence"],
                "average_precision": yearly["average_precision"],
                "roc_auc": yearly["roc_auc"],
                "mean_daily_rank_ic": yearly["mean_daily_rank_ic"],
                "top_minus_bottom_event_rate": yearly["top_minus_bottom_event_rate"],
            }
        )
    annual = pd.DataFrame(annual_rows)
    deciles = decile_table(modern, "risk_score")
    rank_ic = daily_rank_ic(modern, "risk_score")

    summary = {
        "specification_version": config["project"]["specification_version"],
        "model_selected_on_legacy_validation": selected.name,
        "final_model_training_observations": int(len(development)),
        "modern_period_first_signal": str(modern["date"].min().date()),
        "modern_period_last_signal_with_full_target": str(modern["date"].max().date()),
        "membership_tickers": int(membership.shape[1]),
        "median_membership_price_coverage": float(coverage["coverage_rate"].median()),
        "tickers_below_95pct_coverage": coverage.loc[
            coverage["coverage_rate"] < 0.95, "ticker"
        ].tolist(),
        "scores": comparisons,
    }

    output_dir = PROJECT_ROOT / "reports" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(output_dir / "modern_membership_coverage.csv", index=False)
    deciles.to_csv(output_dir / "modern_model_deciles.csv", index=False)
    annual.to_csv(output_dir / "modern_model_annual.csv", index=False)
    rank_ic.rename_axis("date").reset_index().to_csv(
        output_dir / "modern_model_daily_rank_ic.csv", index=False
    )
    modern[["date", "ticker", "target", "future_min_return", "risk_score"]].to_csv(
        output_dir / "modern_model_predictions.csv.gz", index=False, compression="gzip"
    )
    (output_dir / "modern_replication_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
