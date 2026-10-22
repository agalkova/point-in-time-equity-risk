from __future__ import annotations

import pandas as pd


def future_min_return(price: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Worst return from price at t during rows t+1 through t+horizon.

    The current row is excluded, and a label is unavailable unless the full
    future horizon exists.
    """
    if horizon <= 0:
        raise ValueError("Horizon must be positive")
    future_prices = price.shift(-1)
    future_minimum = (
        future_prices.iloc[::-1].rolling(horizon, min_periods=horizon).min().iloc[::-1]
    )
    return future_minimum.div(price).sub(1.0)


def drawdown_event(price: pd.DataFrame, horizon: int, threshold: float) -> pd.DataFrame:
    if threshold >= 0:
        raise ValueError("Drawdown threshold must be negative")
    outcome = future_min_return(price, horizon)
    event = outcome.le(threshold).astype("boolean")
    return event.mask(outcome.isna())


def drawdown_severity(price: pd.DataFrame, horizon: int) -> pd.DataFrame:
    return future_min_return(price, horizon).mul(-1.0).clip(lower=0.0)


def future_first_breach_days(
    price: pd.DataFrame,
    horizon: int,
    threshold: float,
) -> pd.DataFrame:
    """Trading days from signal date to the first threshold breach; NaN if none."""
    if horizon <= 0:
        raise ValueError("Horizon must be positive")
    if threshold >= 0:
        raise ValueError("Drawdown threshold must be negative")
    result = pd.DataFrame(float("nan"), index=price.index, columns=price.columns)
    for offset in range(1, horizon + 1):
        breached = price.shift(-offset).div(price).sub(1.0).le(threshold)
        result = result.mask(result.isna() & breached, float(offset))
    full_horizon = price.shift(-horizon).notna()
    return result.where(full_horizon)

