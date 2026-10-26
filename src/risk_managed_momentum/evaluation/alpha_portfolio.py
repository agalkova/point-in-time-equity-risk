from __future__ import annotations

from typing import Literal

import pandas as pd

from risk_managed_momentum.evaluation.held_returns import value_held_portfolio

PortfolioMode = Literal["long_only", "long_short", "equal_weight"]


def alpha_target_weights(
    signals: pd.DataFrame,
    *,
    score_column: str,
    mode: PortfolioMode,
    top_n: int,
) -> pd.Series:
    work = signals.dropna(subset=["ticker", score_column]).copy()
    if work.empty:
        return pd.Series(dtype=float)
    tickers = work["ticker"].astype(str)
    if mode == "equal_weight":
        return pd.Series(1.0 / len(work), index=tickers, dtype=float)
    winners = work.nlargest(top_n, score_column)
    if mode == "long_only":
        return pd.Series(1.0 / len(winners), index=winners["ticker"].astype(str), dtype=float)
    if mode == "long_short":
        losers = work.nsmallest(top_n, score_column)
        long_weights = pd.Series(
            0.5 / len(winners), index=winners["ticker"].astype(str), dtype=float
        )
        short_weights = pd.Series(
            -0.5 / len(losers), index=losers["ticker"].astype(str), dtype=float
        )
        return pd.concat([long_weights, short_weights]).groupby(level=0).sum()
    raise ValueError(f"Unsupported portfolio mode: {mode}")


def simulate_alpha_portfolio(
    price: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    score_column: str,
    mode: PortfolioMode,
    top_n: int,
    one_way_cost_bps: float,
    valuation_price: pd.DataFrame | None = None,
) -> pd.DataFrame:
    price = price.sort_index().astype(float)
    valuation = price if valuation_price is None else valuation_price.reindex_like(price)
    returns = valuation.pct_change(fill_method=None)
    work = signals.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.normalize()
    work = work[work["date"].isin(price.index)].copy()
    by_date = {date: group for date, group in work.groupby("date")}
    if not by_date:
        raise ValueError("No signal dates overlap the price panel")
    targets = {
        date: alpha_target_weights(
            group,
            score_column=score_column,
            mode=mode,
            top_n=top_n,
        )
        for date, group in by_date.items()
    }
    weights = pd.Series(0.0, index=price.columns)
    cost_rate = one_way_cost_bps / 10_000.0
    rows = []
    simulation_dates = price.index[price.index >= min(targets)]
    for date in simulation_dates:
        asset_return = returns.loc[date]
        gross_return, weights = value_held_portfolio(weights, asset_return, date=date)

        traded_notional = 0.0
        if date in targets:
            target = targets[date].reindex(price.columns, fill_value=0.0)
            traded_notional = float(target.sub(weights).abs().sum())
            weights = target
        transaction_cost = traded_notional * cost_rate
        rows.append(
            {
                "date": date,
                "net_return": gross_return - transaction_cost,
                "gross_return": gross_return,
                "traded_notional": traded_notional,
                "transaction_cost": transaction_cost,
                "net_exposure": float(weights.sum()),
                "gross_exposure": float(weights.abs().sum()),
                "invested_weight": float(weights.abs().sum()),
                "positions": int((weights != 0.0).sum()),
                "missing_exposure": 0.0,
            }
        )
    return pd.DataFrame(rows)
