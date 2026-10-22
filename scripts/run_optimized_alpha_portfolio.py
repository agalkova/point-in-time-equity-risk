from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from run_alpha_research import annual_returns, load_modern_panel

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.factors import load_french_factors
from risk_managed_momentum.evaluation.alpha_portfolio import simulate_alpha_portfolio
from risk_managed_momentum.evaluation.attribution import factor_regression
from risk_managed_momentum.evaluation.optimized_portfolio import (
    simulate_optimized_alpha_portfolio,
)
from risk_managed_momentum.evaluation.portfolio import performance_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_6_portfolio.toml").open("rb") as handle:
        config = tomllib.load(handle)
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    price, _, _ = load_modern_panel(base_config)
    benchmark_bars = pd.read_csv(base_config["modern_source"]["benchmark_path"])
    benchmark_bars["date"] = pd.to_datetime(benchmark_bars["date"]).dt.normalize()
    benchmark_returns = (
        benchmark_bars.sort_values("date").set_index("date")["close"].pct_change(fill_method=None)
    )
    signals = pd.read_csv(TABLES / "v03_alpha_oof_predictions.csv.gz", parse_dates=["date"])
    optimized, holdings = simulate_optimized_alpha_portfolio(
        price,
        benchmark_returns,
        signals,
        config,
    )
    baseline = simulate_alpha_portfolio(
        price,
        signals,
        score_column="score_ridge",
        mode="long_only",
        top_n=50,
        one_way_cost_bps=float(config["portfolio"]["one_way_cost_bps"]),
    )
    factors = load_french_factors(
        str(PROJECT_ROOT / "data/raw/fama_french/daily_six_factors.csv.gz")
    )
    results = {}
    for name, daily in {"ridge_top50": baseline, "optimized_ridge": optimized}.items():
        results[name] = {
            **performance_summary(daily, benchmark_returns=benchmark_returns),
            "annual_returns": annual_returns(daily),
            "factor_attribution": factor_regression(daily, factors),
        }

    baseline_result = results["ridge_top50"]
    optimized_result = results["optimized_ridge"]
    pass_rule = {
        "sharpe_improved": (
            optimized_result["sharpe_zero_rate"] > baseline_result["sharpe_zero_rate"]
        ),
        "maximum_drawdown_improved": (
            optimized_result["maximum_drawdown"] > baseline_result["maximum_drawdown"]
        ),
        "return_shortfall_within_two_points": (
            optimized_result["annualized_return"]
            >= baseline_result["annualized_return"] - 0.02
        ),
        "factor_alpha_positive": (
            optimized_result["factor_attribution"]["annualized_alpha"] > 0.0
        ),
    }
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": "historical exploratory portfolio-engineering test",
        "results": results,
        "pass_rule": pass_rule,
        "passed": all(pass_rule.values()),
        "optimized_rebalances": int(holdings["date"].nunique()),
        "average_optimized_positions": float(holdings.groupby("date").size().mean()),
        "average_estimated_beta": float(
            holdings.groupby("date")["estimated_beta"].first().mean()
        ),
        "average_estimated_volatility": float(
            holdings.groupby("date")["estimated_volatility"].first().mean()
        ),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    optimized.to_csv(TABLES / "v06_optimized_ridge_daily.csv", index=False)
    holdings.to_csv(TABLES / "v06_optimized_ridge_holdings.csv.gz", index=False, compression="gzip")
    (TABLES / "v06_optimized_portfolio_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
