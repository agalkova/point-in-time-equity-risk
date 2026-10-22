from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from sklearn.base import clone

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.evaluation.portfolio import performance_summary, simulate_portfolio
from risk_managed_momentum.features.build import build_research_dataset, split_research_dataset
from risk_managed_momentum.models.drawdown import select_logistic_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PENALTIES = (0.0, 0.25, 0.5, 1.0)
FREQUENCIES = ("weekly", "monthly")
STRATEGIES = ("momentum", "risk_filtered", "risk_adjusted")


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def add_risk_score(frame: pd.DataFrame, model, feature_columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    result["risk_score"] = model.predict_proba(result[feature_columns])[:, 1]
    return result


def main() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    legacy_price, legacy_volume = load_legacy_wide(
        config["legacy_source"]["price_path"], config["legacy_source"]["volume_path"]
    )
    legacy_dataset = build_research_dataset(legacy_price, legacy_volume, config)
    splits = split_research_dataset(legacy_dataset, config)
    selected = select_logistic_model(
        splits["train"],
        splits["validation"],
        legacy_dataset.feature_columns,
        random_seed=int(config["project"]["random_seed"]),
    )
    validation = add_risk_score(splits["validation"], selected.model, legacy_dataset.feature_columns)

    portfolio_config = config["portfolio"]
    simulation_kwargs = {
        "top_n": int(round(1.0 / float(portfolio_config["maximum_position_weight"]))),
        "maximum_position_weight": float(portfolio_config["maximum_position_weight"]),
        "one_way_cost_bps": float(portfolio_config["one_way_cost_bps"]),
    }
    selected_penalties: dict[str, float] = {}
    validation_rows = []
    for frequency in FREQUENCIES:
        candidates = []
        for penalty in PENALTIES:
            daily = simulate_portfolio(
                legacy_price,
                validation,
                frequency=frequency,
                strategy="risk_adjusted",
                risk_penalty=penalty,
                **simulation_kwargs,
            )
            metrics = performance_summary(daily)
            candidates.append((penalty, metrics))
            validation_rows.append(
                {"frequency": frequency, "risk_penalty": penalty, **metrics}
            )
        selected_penalties[frequency] = max(
            candidates, key=lambda item: item[1]["sharpe_zero_rate"]
        )[0]

    development = pd.concat(splits.values(), ignore_index=True)
    final_model = clone(selected.model).fit(
        development[legacy_dataset.feature_columns], development["target"]
    )
    source = config["modern_source"]
    bars = pd.read_csv(project_path(source["bars_path"]))
    alias_bars = pd.read_csv(project_path(source["historical_alias_bars_path"]))
    bars = pd.concat([bars, alias_bars[bars.columns]], ignore_index=True)
    membership_long = pd.read_csv(project_path(source["membership_path"]))
    with project_path(source["aliases_path"]).open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    modern_price, modern_volume, membership = build_point_in_time_panel(
        bars, membership_long, aliases
    )
    modern_dataset = build_research_dataset(
        modern_price, modern_volume, config, membership=membership
    )
    holdout = config["splits"]["modern_holdout"]
    modern = modern_dataset.frame[
        modern_dataset.frame["date"].between(holdout["start"], holdout["end"])
    ].copy()
    modern = add_risk_score(modern, final_model, modern_dataset.feature_columns)
    benchmark_bars = pd.read_csv(project_path(source["benchmark_path"]))
    benchmark_bars["date"] = pd.to_datetime(benchmark_bars["date"]).dt.normalize()
    benchmark_returns = (
        benchmark_bars.sort_values("date").set_index("date")["close"].pct_change(fill_method=None)
    )

    output_dir = PROJECT_ROOT / "reports" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    portfolio_rows = []
    for frequency in FREQUENCIES:
        for strategy in STRATEGIES:
            penalty = selected_penalties[frequency] if strategy == "risk_adjusted" else 0.0
            daily = simulate_portfolio(
                modern_price,
                modern,
                frequency=frequency,
                strategy=strategy,
                risk_penalty=penalty,
                **simulation_kwargs,
            )
            metrics = performance_summary(daily, benchmark_returns=benchmark_returns)
            portfolio_rows.append(
                {
                    "frequency": frequency,
                    "strategy": strategy,
                    "selected_risk_penalty": penalty,
                    **metrics,
                }
            )
            daily.to_csv(
                output_dir / f"portfolio_{frequency}_{strategy}_daily.csv",
                index=False,
            )

        momentum_daily = pd.read_csv(output_dir / f"portfolio_{frequency}_momentum_daily.csv")
        period_start = pd.to_datetime(momentum_daily["date"].iloc[0])
        period_end = pd.to_datetime(momentum_daily["date"].iloc[-1])
        benchmark_period = benchmark_returns.loc[period_start:period_end].dropna()
        benchmark_daily = pd.DataFrame(
            {
                "date": benchmark_period.index,
                "net_return": benchmark_period.to_numpy(),
                "gross_return": benchmark_period.to_numpy(),
                "traded_notional": 0.0,
                "transaction_cost": 0.0,
                "invested_weight": 1.0,
                "positions": 1,
                "missing_exposure": 0.0,
            }
        )
        if not benchmark_daily.empty:
            benchmark_daily.loc[benchmark_daily.index[0], "net_return"] -= (
                simulation_kwargs["one_way_cost_bps"] / 10_000.0
            )
            benchmark_daily.loc[benchmark_daily.index[0], "traded_notional"] = 1.0
            benchmark_daily.loc[benchmark_daily.index[0], "transaction_cost"] = (
                simulation_kwargs["one_way_cost_bps"] / 10_000.0
            )
        portfolio_rows.append(
            {
                "frequency": frequency,
                "strategy": "spy_buy_hold",
                "selected_risk_penalty": 0.0,
                **performance_summary(benchmark_daily, benchmark_returns=benchmark_returns),
            }
        )
        benchmark_daily.to_csv(
            output_dir / f"portfolio_{frequency}_spy_buy_hold_daily.csv", index=False
        )

    validation_table = pd.DataFrame(validation_rows)
    portfolio_table = pd.DataFrame(portfolio_rows)
    validation_table.to_csv(output_dir / "portfolio_penalty_selection.csv", index=False)
    portfolio_table.to_csv(output_dir / "portfolio_modern_summary.csv", index=False)
    summary = {
        "selected_model": selected.name,
        "selection_period": config["splits"]["validation"],
        "selected_risk_penalties": selected_penalties,
        "one_way_cost_bps": simulation_kwargs["one_way_cost_bps"],
        "maximum_position_weight": simulation_kwargs["maximum_position_weight"],
        "modern_results": portfolio_rows,
    }
    (output_dir / "portfolio_experiment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
