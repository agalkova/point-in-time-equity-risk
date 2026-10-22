from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from sklearn.base import clone

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.factors import load_french_factors
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.evaluation.alpha import alpha_score_summary, monthly_rank_ic
from risk_managed_momentum.evaluation.alpha_portfolio import simulate_alpha_portfolio
from risk_managed_momentum.evaluation.attribution import factor_regression
from risk_managed_momentum.evaluation.portfolio import performance_summary
from risk_managed_momentum.evaluation.ranking import moving_block_interval
from risk_managed_momentum.evaluation.walk_forward import expanding_year_folds
from risk_managed_momentum.features.alpha import build_alpha_dataset
from risk_managed_momentum.models.alpha import alpha_model_factories

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports" / "tables"


def load_alpha_config() -> dict:
    with (PROJECT_ROOT / "configs" / "research_v0_3_alpha.toml").open("rb") as handle:
        return tomllib.load(handle)


def load_modern_panel(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = config["modern_source"]
    bars = pd.read_csv(source["bars_path"])
    aliases = pd.read_csv(source["historical_alias_bars_path"])
    bars = pd.concat([bars, aliases[bars.columns]], ignore_index=True)
    membership = pd.read_csv(source["membership_path"])
    with Path(source["aliases_path"]).open("rb") as handle:
        ticker_aliases = tomllib.load(handle)["alias"]
    return build_point_in_time_panel(bars, membership, ticker_aliases)


def add_same_date_rank(frame: pd.DataFrame, source: str, destination: str) -> None:
    frame[destination] = frame.groupby("date")[source].rank(method="average", pct=True)


def annual_returns(daily: pd.DataFrame) -> list[dict[str, float | int]]:
    work = daily.copy()
    work["year"] = pd.to_datetime(work["date"]).dt.year
    return [
        {
            "year": int(year),
            "return": float((1.0 + group["net_return"]).prod() - 1.0),
        }
        for year, group in work.groupby("year")
    ]


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    config = load_alpha_config()
    price, volume, membership = load_modern_panel(base_config)
    dataset = build_alpha_dataset(price, volume, base_config, config, membership)
    frame = dataset.frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()

    validation = config["validation"]
    folds = expanding_year_folds(
        frame["date"],
        first_test_year=int(validation["first_test_year"]),
        last_test_year=int(validation["last_test_year"]),
        purge_trading_days=int(validation["purge_month_end_signals"]),
    )
    factories = alpha_model_factories(config)
    outputs = []
    fold_rows = []
    for fold in folds:
        train = frame[frame["date"].isin(fold.train_dates)].copy()
        test = frame[frame["date"].isin(fold.test_dates)].copy()
        if len(train) < int(validation["minimum_training_observations"]) or test.empty:
            continue
        for name, prototype in factories.items():
            model = clone(prototype).fit(
                train[dataset.feature_columns], train["future_residual_return_21"]
            )
            test[f"prediction_{name}"] = model.predict(test[dataset.feature_columns])
            add_same_date_rank(test, f"prediction_{name}", f"score_{name}")

        ensemble = config["ensemble"]
        test["score_ensemble"] = (
            float(ensemble["ridge_weight"]) * test["score_ridge"]
            + float(ensemble["hist_gradient_boosting_weight"])
            * test["score_hist_gradient_boosting"]
        )
        test["score_fixed_momentum"] = (
            0.40 * test["rank_momentum_12_1"]
            + 0.30 * test["rank_momentum_6_1"]
            + 0.20 * test["rank_momentum_3_1"]
            + 0.10 * (1.0 - test["rank_return_1m"])
        )
        test["score_risk_adjusted"] = test["score_ensemble"] - float(
            config["portfolio"]["risk_penalty"]
        ) * test["risk_composite"]
        for name in [
            "ridge",
            "hist_gradient_boosting",
            "ensemble",
            "fixed_momentum",
            "risk_adjusted",
        ]:
            metrics = alpha_score_summary(test, f"score_{name}")
            fold_rows.append({"test_year": fold.test_year, "model": name, **metrics})
        outputs.append(test)

    if not outputs:
        raise RuntimeError("No alpha walk-forward folds were produced")
    oof = pd.concat(outputs, ignore_index=True).sort_values(["date", "ticker"])
    score_names = [
        "ridge",
        "hist_gradient_boosting",
        "ensemble",
        "fixed_momentum",
        "risk_adjusted",
    ]
    pooled = {}
    for name in score_names:
        score_column = f"score_{name}"
        metrics = alpha_score_summary(oof, score_column)
        rank_ic = monthly_rank_ic(oof, score_column)
        lower, upper = moving_block_interval(
            rank_ic,
            block_length=int(config["inference"]["block_length_months"]),
            iterations=int(config["inference"]["bootstrap_iterations"]),
            random_seed=int(config["project"]["random_seed"]),
        )
        pooled[name] = {**metrics, "rank_ic_block_interval": [lower, upper]}

    benchmark_bars = pd.read_csv(base_config["modern_source"]["benchmark_path"])
    benchmark_bars["date"] = pd.to_datetime(benchmark_bars["date"]).dt.normalize()
    benchmark_returns = (
        benchmark_bars.sort_values("date").set_index("date")["close"].pct_change(fill_method=None)
    )
    factor_path = PROJECT_ROOT / "data" / "raw" / "fama_french" / "daily_six_factors.csv.gz"
    factors = load_french_factors(str(factor_path)) if factor_path.exists() else None

    portfolio_config = config["portfolio"]
    portfolio_specs = {
        "ensemble_long_only": ("score_ensemble", "long_only"),
        "fixed_momentum_long_only": ("score_fixed_momentum", "long_only"),
        "risk_adjusted_long_only": ("score_risk_adjusted", "long_only"),
        "ensemble_long_short": ("score_ensemble", "long_short"),
        "equal_weight_universe": ("score_ensemble", "equal_weight"),
        # These individual-model portfolios are sensitivity diagnostics added after
        # the primary ensemble result. They cannot support a confirmatory claim.
        "ridge_long_only_post_spec": ("score_ridge", "long_only"),
        "ridge_long_short_post_spec": ("score_ridge", "long_short"),
        "boosting_long_only_post_spec": ("score_hist_gradient_boosting", "long_only"),
    }
    portfolio_results = {}
    for name, (score_column, mode) in portfolio_specs.items():
        daily = simulate_alpha_portfolio(
            price,
            oof,
            score_column=score_column,
            mode=mode,
            top_n=int(portfolio_config["top_n"]),
            one_way_cost_bps=float(portfolio_config["one_way_cost_bps"]),
        )
        result = {
            **performance_summary(daily, benchmark_returns=benchmark_returns),
            "annual_returns": annual_returns(daily),
        }
        if factors is not None:
            result["factor_attribution"] = factor_regression(
                daily,
                factors,
                subtract_risk_free_rate=mode != "long_short",
            )
        portfolio_results[name] = result
        daily.to_csv(TABLES / f"v03_{name}_daily.csv", index=False)

    first_portfolio_date = pd.Timestamp(oof["date"].min())
    benchmark_period = benchmark_returns.loc[first_portfolio_date : price.index.max()].dropna()
    benchmark_daily = pd.DataFrame(
        {
            "date": benchmark_period.index,
            "net_return": benchmark_period.to_numpy(),
            "gross_return": benchmark_period.to_numpy(),
            "traded_notional": 0.0,
            "transaction_cost": 0.0,
            "invested_weight": 1.0,
            "missing_exposure": 0.0,
        }
    )
    if not benchmark_daily.empty:
        initial_cost = float(portfolio_config["one_way_cost_bps"]) / 10_000.0
        benchmark_daily.loc[benchmark_daily.index[0], "net_return"] -= initial_cost
        benchmark_daily.loc[benchmark_daily.index[0], "transaction_cost"] = initial_cost
        benchmark_daily.loc[benchmark_daily.index[0], "traded_notional"] = 1.0
    benchmark_result = {
        **performance_summary(benchmark_daily, benchmark_returns=benchmark_returns),
        "annual_returns": annual_returns(benchmark_daily),
    }
    if factors is not None:
        benchmark_result["factor_attribution"] = factor_regression(benchmark_daily, factors)
    portfolio_results["spy_buy_hold"] = benchmark_result
    benchmark_daily.to_csv(TABLES / "v03_spy_buy_hold_daily.csv", index=False)

    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": "exploratory; confirmation requires prospective or independent data",
        "features": len(dataset.feature_columns),
        "out_of_fold_observations": len(oof),
        "out_of_fold_months": int(oof["date"].nunique()),
        "test_years": sorted(oof["date"].dt.year.unique().astype(int).tolist()),
        "pooled_predictive_results": pooled,
        "portfolio_results": portfolio_results,
        "post_specification_portfolio_diagnostics": [
            "ridge_long_only_post_spec",
            "ridge_long_short_post_spec",
            "boosting_long_only_post_spec",
        ],
        "factor_data_available": factors is not None,
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(TABLES / "v03_alpha_walk_forward_folds.csv", index=False)
    oof[
        [
            "date",
            "ticker",
            "future_return_21",
            "future_residual_return_21",
            "risk_composite",
            *[f"score_{name}" for name in score_names],
        ]
    ].to_csv(TABLES / "v03_alpha_oof_predictions.csv.gz", index=False, compression="gzip")
    (TABLES / "v03_alpha_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
