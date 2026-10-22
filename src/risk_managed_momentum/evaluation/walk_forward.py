from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardFold:
    test_year: int
    train_dates: pd.DatetimeIndex
    test_dates: pd.DatetimeIndex


def expanding_year_folds(
    dates: Iterable[object],
    *,
    first_test_year: int,
    last_test_year: int,
    purge_trading_days: int,
) -> list[WalkForwardFold]:
    unique = pd.DatetimeIndex(pd.to_datetime(pd.Series(list(dates))).dropna().unique()).sort_values()
    if purge_trading_days < 0:
        raise ValueError("Purge trading days cannot be negative")
    folds = []
    for year in range(first_test_year, last_test_year + 1):
        test_dates = unique[unique.year == year]
        earlier = unique[unique < pd.Timestamp(year=year, month=1, day=1)]
        if len(test_dates) == 0 or len(earlier) <= purge_trading_days:
            continue
        train_dates = earlier[:-purge_trading_days] if purge_trading_days else earlier
        folds.append(WalkForwardFold(year, train_dates, test_dates))
    return folds
