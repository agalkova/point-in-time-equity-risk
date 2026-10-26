from __future__ import annotations

import pandas as pd


def value_held_portfolio(
    weights: pd.Series,
    asset_return: pd.Series,
    *,
    date: pd.Timestamp,
) -> tuple[float, pd.Series]:
    """Apply one day of returns and fail closed on missing held-security values."""
    aligned = asset_return.reindex(weights.index)
    missing = weights.abs().gt(1e-12) & aligned.isna()
    if missing.any():
        tickers = sorted(weights.index[missing].astype(str).tolist())
        raise ValueError(f"Missing held-security returns on {date.date()}: {tickers}")
    gross_return = float((weights * aligned.fillna(0.0)).sum())
    updated = weights.copy()
    if 1.0 + gross_return > 0.0:
        updated = weights.mul(1.0 + aligned.fillna(0.0)).div(1.0 + gross_return)
    return gross_return, updated
