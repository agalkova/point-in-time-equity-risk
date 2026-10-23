from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from risk_managed_momentum.features.build import ResearchDataset, build_research_dataset
from risk_managed_momentum.features.targets import future_first_breach_days


def _flatten(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename_axis("date").rename_axis("ticker", axis=1).stack().rename("value").reset_index()


def _rank(frame: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    return frame.where(membership).rank(axis=1, method="average", pct=True)


def build_advanced_research_dataset(
    price: pd.DataFrame,
    volume: pd.DataFrame,
    config: dict[str, Any],
    membership: pd.DataFrame | None = None,
    *,
    include_unlabeled: bool = False,
) -> ResearchDataset:
    """Extend the v0.1 table with fixed nonlinear-model candidate features."""
    price = price.sort_index().astype(float)
    volume = volume.reindex(index=price.index, columns=price.columns).astype(float)
    member = price.notna() if membership is None else membership.reindex_like(price).fillna(False)
    returns = price.pct_change(fill_method=None)

    downside20 = returns.clip(upper=0.0).pow(2).rolling(20, min_periods=15).mean().pow(0.5)
    downside60 = returns.clip(upper=0.0).pow(2).rolling(60, min_periods=40).mean().pow(0.5)
    skew20 = returns.rolling(20, min_periods=15).skew()
    skew60 = returns.rolling(60, min_periods=40).skew()
    kurtosis60 = returns.rolling(60, min_periods=40).kurt()
    maximum_drawdown60 = price.div(price.rolling(60, min_periods=40).max()).sub(1.0)
    maximum_drawdown120 = price.div(price.rolling(120, min_periods=80).max()).sub(1.0)
    lower_tail60 = returns.rolling(60, min_periods=40).quantile(0.05)
    autocorrelation20 = returns.rolling(20, min_periods=15).corr(returns.shift(1))
    price_volume_correlation20 = returns.rolling(20, min_periods=15).corr(
        np.log(volume.where(volume > 0.0)).diff()
    )
    dollar_volume = price.mul(volume).where(lambda value: value > 0.0)
    amihud60 = returns.abs().div(dollar_volume).rolling(60, min_periods=40).mean()

    advanced = {
        "rank_downside_semivolatility_20": _rank(downside20, member),
        "rank_downside_semivolatility_60": _rank(downside60, member),
        "rank_return_skewness_20": _rank(skew20, member),
        "rank_return_skewness_60": _rank(skew60, member),
        "rank_return_kurtosis_60": _rank(kurtosis60, member),
        "rank_trailing_maximum_drawdown_60": _rank(maximum_drawdown60, member),
        "rank_trailing_maximum_drawdown_120": _rank(maximum_drawdown120, member),
        "rank_lower_tail_return_60": _rank(lower_tail60, member),
        "rank_return_autocorrelation_20": _rank(autocorrelation20, member),
        "rank_price_volume_correlation_20": _rank(price_volume_correlation20, member),
        "rank_amihud_illiquidity_60": _rank(amihud60, member),
    }

    base = build_research_dataset(
        price,
        volume,
        config,
        membership=member,
        include_unlabeled=include_unlabeled,
    )
    frame = base.frame.copy()
    for name, values in advanced.items():
        long = _flatten(values).rename(columns={"value": name})
        frame = frame.merge(long, on=["date", "ticker"], how="left", validate="one_to_one")

    target = config["target"]
    breach = future_first_breach_days(
        price,
        horizon=int(target["horizon_days"]),
        threshold=float(target["drawdown_threshold"]),
    )
    breach_long = _flatten(breach).rename(columns={"value": "first_breach_days"})
    frame = frame.merge(
        breach_long, on=["date", "ticker"], how="left", validate="one_to_one"
    )
    feature_columns = base.feature_columns + list(advanced)
    return ResearchDataset(frame=frame, feature_columns=feature_columns)
