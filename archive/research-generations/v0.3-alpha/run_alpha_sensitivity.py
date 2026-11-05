from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.factors import load_french_factors
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.evaluation.alpha_portfolio import simulate_alpha_portfolio
from risk_managed_momentum.evaluation.attribution import factor_regression
from risk_managed_momentum.evaluation.portfolio import performance_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports" / "tables"
POSITION_COUNTS = (25, 50, 100)
COSTS_BPS = (5.0, 10.0, 20.0)


def load_modern_price(config: dict) -> pd.DataFrame:
    source = config["modern_source"]
    bars = pd.read_csv(source["bars_path"])
    aliases = pd.read_csv(source["historical_alias_bars_path"])
    bars = pd.concat([bars, aliases[bars.columns]], ignore_index=True)
    membership = pd.read_csv(source["membership_path"])
    with Path(source["aliases_path"]).open("rb") as handle:
        ticker_aliases = tomllib.load(handle)["alias"]
    price, _, _ = build_point_in_time_panel(bars, membership, ticker_aliases)
    return price


def main() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    price = load_modern_price(config)
    signals = pd.read_csv(TABLES / "v03_alpha_oof_predictions.csv.gz", parse_dates=["date"])
    factors = load_french_factors(
        str(PROJECT_ROOT / "data" / "raw" / "fama_french" / "daily_six_factors.csv.gz")
    )
    rows = []
    for mode in ("long_only", "long_short"):
        for top_n in POSITION_COUNTS:
            for cost_bps in COSTS_BPS:
                daily = simulate_alpha_portfolio(
                    price,
                    signals,
                    score_column="score_ridge",
                    mode=mode,
                    top_n=top_n,
                    one_way_cost_bps=cost_bps,
                )
                performance = performance_summary(daily)
                attribution = factor_regression(
                    daily,
                    factors,
                    subtract_risk_free_rate=mode != "long_short",
                )
                rows.append(
                    {
                        "mode": mode,
                        "positions_per_side": top_n,
                        "one_way_cost_bps": cost_bps,
                        **performance,
                        **attribution,
                    }
                )
    result = pd.DataFrame(rows)
    result.to_csv(TABLES / "v03_ridge_portfolio_sensitivity.csv", index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
