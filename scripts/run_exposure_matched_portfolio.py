from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.evaluation.portfolio import performance_summary, simulate_portfolio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports" / "tables"


def load_modern_panel(config: dict) -> pd.DataFrame:
    source = config["modern_source"]
    bars = pd.read_csv(source["bars_path"])
    alias_bars = pd.read_csv(source["historical_alias_bars_path"])
    bars = pd.concat([bars, alias_bars[bars.columns]], ignore_index=True)
    membership = pd.read_csv(source["membership_path"])
    with Path(source["aliases_path"]).open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    price, _, _ = build_point_in_time_panel(bars, membership, aliases)
    return price


def main() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    price = load_modern_panel(config)
    signals = pd.read_csv(
        TABLES / "v02_out_of_fold_predictions.csv.gz",
        parse_dates=["date"],
    ).rename(columns={"score_ensemble": "risk_score"})

    # Forty positions at a 2% cap gives both strategies the same 80% target gross
    # exposure whenever at least 40 securities pass their selection rule.
    settings = {
        "frequency": "monthly",
        "top_n": 40,
        "maximum_position_weight": 0.02,
        "one_way_cost_bps": 10.0,
    }
    rows = []
    daily_results = {}
    for strategy in ("momentum", "risk_filtered"):
        daily = simulate_portfolio(price, signals, strategy=strategy, **settings)
        daily_results[strategy] = daily
        metrics = performance_summary(daily)
        rows.append({"strategy": strategy, **settings, **metrics})
        daily.to_csv(TABLES / f"v02_exposure_matched_{strategy}_daily.csv", index=False)

    # Re-scale the ordinary momentum return stream to the filter's realized daily
    # gross exposure. This isolates the security-selection effect from holding cash.
    momentum = daily_results["momentum"].copy()
    filtered = daily_results["risk_filtered"].set_index("date")
    exposure = filtered["invested_weight"].reindex(momentum["date"]).to_numpy()
    multiplier = exposure / momentum["invested_weight"].replace(0.0, float("nan"))
    multiplier = multiplier.fillna(0.0)
    momentum["gross_return"] *= multiplier
    momentum["transaction_cost"] *= multiplier
    momentum["traded_notional"] *= multiplier
    momentum["net_return"] = momentum["gross_return"] - momentum["transaction_cost"]
    momentum["invested_weight"] = exposure
    matched_metrics = performance_summary(momentum)
    rows.append({"strategy": "cash_matched_momentum", **settings, **matched_metrics})
    momentum.to_csv(TABLES / "v02_exposure_matched_cash_matched_momentum_daily.csv", index=False)

    result = pd.DataFrame(rows)
    result.to_csv(TABLES / "v02_exposure_matched_portfolio.csv", index=False)
    payload = {
        "purpose": "Separate security-selection effects from the cash-exposure confound.",
        "signal": "walk-forward out-of-fold ensemble drawdown risk",
        "cash_match": "Ordinary momentum returns and costs scaled to the filter's daily gross exposure.",
        "settings": settings,
        "results": rows,
    }
    (TABLES / "v02_exposure_matched_portfolio.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
