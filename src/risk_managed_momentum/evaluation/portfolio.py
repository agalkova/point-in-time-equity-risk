from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from risk_managed_momentum.evaluation.held_returns import value_held_portfolio

Frequency = Literal["weekly", "monthly"]
Strategy = Literal["momentum", "risk_filtered", "risk_adjusted"]


def rebalance_dates(signal_dates: pd.Series, frequency: Frequency) -> list[pd.Timestamp]:
    dates = pd.Series(pd.to_datetime(signal_dates).drop_duplicates()).sort_values()
    if frequency == "weekly":
        iso = dates.dt.isocalendar()
        key = iso["year"].astype(str) + "-" + iso["week"].astype(str)
    elif frequency == "monthly":
        key = dates.dt.to_period("M").astype(str)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return dates.groupby(key).max().tolist()


def target_weights(
    signals: pd.DataFrame,
    *,
    strategy: Strategy,
    risk_penalty: float = 0.0,
    top_n: int = 50,
    maximum_position_weight: float = 0.02,
) -> pd.Series:
    required = {"ticker", "rank_ret_60", "risk_score"}
    missing = required - set(signals.columns)
    if missing:
        raise ValueError(f"Signals missing columns: {sorted(missing)}")
    work = signals.dropna(subset=list(required)).copy()
    if work.empty:
        return pd.Series(dtype=float)
    work["momentum_rank"] = work["rank_ret_60"].rank(pct=True, method="average")
    work["risk_rank"] = work["risk_score"].rank(pct=True, method="average")
    if strategy == "momentum":
        work["portfolio_score"] = work["momentum_rank"]
    elif strategy == "risk_filtered":
        work = work[work["risk_rank"] <= 0.80].copy()
        work["portfolio_score"] = work["momentum_rank"]
    elif strategy == "risk_adjusted":
        work["portfolio_score"] = work["momentum_rank"] - risk_penalty * work["risk_rank"]
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    selected = work.nlargest(top_n, "portfolio_score")
    if selected.empty:
        return pd.Series(dtype=float)
    weight = min(1.0 / len(selected), maximum_position_weight)
    return pd.Series(weight, index=selected["ticker"].astype(str), dtype=float)


def simulate_portfolio(
    price: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    frequency: Frequency,
    strategy: Strategy,
    risk_penalty: float = 0.0,
    top_n: int = 50,
    maximum_position_weight: float = 0.02,
    one_way_cost_bps: float = 10.0,
    valuation_price: pd.DataFrame | None = None,
) -> pd.DataFrame:
    price = price.sort_index().astype(float)
    valuation = price if valuation_price is None else valuation_price.reindex_like(price)
    returns = valuation.pct_change(fill_method=None)
    work = signals.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.normalize()
    dates = rebalance_dates(work["date"], frequency)
    by_date = {date: group for date, group in work.groupby("date")}
    dates = [date for date in dates if date in price.index and date in by_date]
    if not dates:
        raise ValueError("No rebalance dates overlap prices and signals")

    targets = {
        date: target_weights(
            by_date[date],
            strategy=strategy,
            risk_penalty=risk_penalty,
            top_n=top_n,
            maximum_position_weight=maximum_position_weight,
        )
        for date in dates
    }
    weights = pd.Series(0.0, index=price.columns)
    rows = []
    cost_rate = one_way_cost_bps / 10_000.0
    simulation_dates = price.index[(price.index >= min(dates)) & (price.index <= max(dates))]
    for date in simulation_dates:
        asset_return = returns.loc[date]
        gross_return, weights = value_held_portfolio(weights, asset_return, date=date)

        traded_notional = 0.0
        if date in targets:
            target = targets[date].reindex(price.columns, fill_value=0.0)
            traded_notional = float(target.sub(weights).abs().sum())
            weights = target
        cost = traded_notional * cost_rate
        rows.append(
            {
                "date": date,
                "net_return": gross_return - cost,
                "gross_return": gross_return,
                "traded_notional": traded_notional,
                "transaction_cost": cost,
                "invested_weight": float(weights.sum()),
                "positions": int((weights > 0.0).sum()),
                "missing_exposure": 0.0,
            }
        )
    return pd.DataFrame(rows)


def performance_summary(
    daily: pd.DataFrame,
    benchmark_returns: pd.Series | None = None,
) -> dict[str, float | int]:
    returns = daily["net_return"].dropna()
    if returns.empty:
        raise ValueError("Portfolio has no returns")
    wealth = (1.0 + returns).cumprod()
    years = len(returns) / 252.0
    annual_return = float(wealth.iloc[-1] ** (1.0 / years) - 1.0) if years else float("nan")
    annual_volatility = float(returns.std(ddof=1) * np.sqrt(252.0))
    downside = returns.clip(upper=0.0)
    downside_volatility = float(np.sqrt((downside.pow(2)).mean()) * np.sqrt(252.0))
    drawdown = wealth.div(wealth.cummax()).sub(1.0)
    result: dict[str, float | int] = {
        "trading_days": len(returns),
        "cumulative_return": float(wealth.iloc[-1] - 1.0),
        "annualized_return": annual_return,
        "annualized_volatility": annual_volatility,
        "sharpe_zero_rate": annual_return / annual_volatility
        if annual_volatility
        else float("nan"),
        "sortino_zero_rate": annual_return / downside_volatility
        if downside_volatility
        else float("nan"),
        "maximum_drawdown": float(drawdown.min()),
        "annualized_traded_notional": float(daily["traded_notional"].sum() / years),
        "total_transaction_cost": float(daily["transaction_cost"].sum()),
        "average_invested_weight": float(daily["invested_weight"].mean()),
        "days_with_missing_exposure": int((daily["missing_exposure"] > 0.0).sum()),
    }
    if benchmark_returns is not None:
        aligned = pd.concat(
            [
                pd.Series(
                    returns.to_numpy(), index=pd.to_datetime(daily.loc[returns.index, "date"])
                ),
                benchmark_returns.rename("benchmark"),
            ],
            axis=1,
            join="inner",
        ).dropna()
        portfolio_return = aligned.iloc[:, 0]
        benchmark = aligned["benchmark"]
        benchmark_variance = float(benchmark.var(ddof=1))
        result["benchmark_beta"] = (
            float(portfolio_return.cov(benchmark) / benchmark_variance)
            if benchmark_variance
            else float("nan")
        )
        result["benchmark_correlation"] = float(portfolio_return.corr(benchmark))
    return result
