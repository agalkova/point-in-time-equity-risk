from __future__ import annotations

import numpy as np
import pandas as pd


def _signal_counts(
    dates: pd.DatetimeIndex,
    tickers: pd.Index,
    episodes: pd.DataFrame,
    *,
    holding_period: int,
    entry_delay: int,
) -> pd.DataFrame:
    counts = pd.DataFrame(0.0, index=dates, columns=tickers)
    date_positions = pd.Series(np.arange(len(dates)), index=dates)
    for row in episodes[["date", "ticker"]].itertuples(index=False):
        if row.date not in date_positions.index or row.ticker not in counts.columns:
            continue
        signal_position = int(date_positions.loc[row.date])
        start = signal_position + int(entry_delay)
        end = min(start + int(holding_period), len(dates) - 1)
        if start < end:
            counts.iloc[start:end, counts.columns.get_loc(row.ticker)] += 1.0
    return counts


def _normalized_weights(counts: pd.DataFrame) -> pd.DataFrame:
    gross = counts.sum(axis=1).replace(0.0, np.nan)
    return counts.div(gross, axis=0).fillna(0.0)


def episode_overlay_returns(
    price: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    risk_column: str,
    high_risk_threshold: float,
    holding_period: int,
    entry_delay: int,
    one_way_cost_bps: float,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Compare all episode cohorts with a fixed high-risk exclusion overlay."""
    price = price.sort_index()
    episodes = episodes.copy()
    baseline_counts = _signal_counts(
        price.index,
        price.columns,
        episodes,
        holding_period=holding_period,
        entry_delay=entry_delay,
    )
    retained = episodes[episodes[risk_column].lt(float(high_risk_threshold))]
    overlay_counts = _signal_counts(
        price.index,
        price.columns,
        retained,
        holding_period=holding_period,
        entry_delay=entry_delay,
    )
    baseline_weights = _normalized_weights(baseline_counts)
    overlay_weights = _normalized_weights(overlay_counts)
    next_return = price.shift(-1).div(price).sub(1.0)
    cost_rate = float(one_way_cost_bps) / 10000.0
    baseline_turnover = baseline_weights.diff().abs().sum(axis=1).fillna(
        baseline_weights.abs().sum(axis=1)
    )
    overlay_turnover = overlay_weights.diff().abs().sum(axis=1).fillna(
        overlay_weights.abs().sum(axis=1)
    )
    result = pd.DataFrame(index=price.index)
    result["baseline_gross_return"] = (baseline_weights * next_return).sum(axis=1)
    result["overlay_gross_return"] = (overlay_weights * next_return).sum(axis=1)
    result["baseline_turnover"] = baseline_turnover
    result["overlay_turnover"] = overlay_turnover
    result["baseline_net_return"] = result["baseline_gross_return"] - cost_rate * baseline_turnover
    result["overlay_net_return"] = result["overlay_gross_return"] - cost_rate * overlay_turnover
    result["baseline_invested"] = baseline_weights.sum(axis=1).gt(0.0)
    result["overlay_invested"] = overlay_weights.sum(axis=1).gt(0.0)
    active = result["baseline_invested"]
    if active.any():
        first = active[active].index.min()
        last = active[active].index.max()
        result = result.loc[first:last].copy()
    diagnostics = {
        "episodes": len(episodes),
        "excluded_episodes": int(len(episodes) - len(retained)),
        "exclusion_rate": float(1.0 - len(retained) / len(episodes)),
        "baseline_invested_day_rate": float(result["baseline_invested"].mean()),
        "overlay_invested_day_rate": float(result["overlay_invested"].mean()),
    }
    return result, diagnostics


def portfolio_summary(returns: pd.Series, turnover: pd.Series, annualization_days: int) -> dict[str, float]:
    returns = returns.fillna(0.0)
    wealth = (1.0 + returns).cumprod()
    years = len(returns) / float(annualization_days)
    annual_return = float(wealth.iloc[-1] ** (1.0 / years) - 1.0) if years else np.nan
    annual_volatility = float(returns.std(ddof=1) * np.sqrt(annualization_days))
    sharpe = (
        float(returns.mean() / returns.std(ddof=1) * np.sqrt(annualization_days))
        if returns.std(ddof=1) > 0.0
        else np.nan
    )
    drawdown = wealth.div(wealth.cummax()).sub(1.0)
    return {
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe_ratio": sharpe,
        "maximum_drawdown": float(drawdown.min()),
        "average_daily_turnover": float(turnover.mean()),
        "final_wealth": float(wealth.iloc[-1]),
    }

