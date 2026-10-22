from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LegacyAudit:
    rows: int
    securities: int
    start: str
    end: str
    price_missing_cells: int
    volume_missing_cells: int
    duplicate_dates: int
    duplicate_tickers: int
    nonpositive_prices: int
    negative_volumes: int
    mismatched_missing_cells: int

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


def load_legacy_wide(
    price_path: str | Path,
    volume_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and align the original wide price and volume matrices."""
    price = pd.read_pickle(Path(price_path)).sort_index().astype(float)
    volume = pd.read_pickle(Path(volume_path)).sort_index().astype(float)

    if not isinstance(price.index, pd.DatetimeIndex):
        raise TypeError("Price index must be a DatetimeIndex")
    if not isinstance(volume.index, pd.DatetimeIndex):
        raise TypeError("Volume index must be a DatetimeIndex")
    if not price.index.equals(volume.index):
        raise ValueError("Price and volume dates do not match")
    if not price.columns.equals(volume.columns):
        raise ValueError("Price and volume ticker columns do not match")
    return price, volume


def audit_legacy_wide(price: pd.DataFrame, volume: pd.DataFrame) -> LegacyAudit:
    """Return compact data-contract checks without changing source values."""
    mismatched_missing = price.isna().ne(volume.isna())
    return LegacyAudit(
        rows=int(len(price)),
        securities=int(len(price.columns)),
        start=str(price.index.min().date()),
        end=str(price.index.max().date()),
        price_missing_cells=int(price.isna().sum().sum()),
        volume_missing_cells=int(volume.isna().sum().sum()),
        duplicate_dates=int(price.index.duplicated().sum()),
        duplicate_tickers=int(price.columns.duplicated().sum()),
        nonpositive_prices=int(np.isfinite(price.to_numpy()).astype(bool)[price.to_numpy() <= 0].sum()),
        negative_volumes=int((volume < 0).sum().sum()),
        mismatched_missing_cells=int(mismatched_missing.sum().sum()),
    )

