from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AlphaDataset:
    frame: pd.DataFrame
    feature_columns: list[str]


def _rank(frame: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    return frame.where(membership).rank(axis=1, method="average", pct=True)


def _flatten(frame: pd.DataFrame, index: pd.MultiIndex) -> np.ndarray:
    dates = index.levels[0]
    tickers = index.levels[1]
    return frame.reindex(index=dates, columns=tickers).to_numpy().reshape(-1)


def month_end_trading_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(index).sort_values().unique()
    return pd.DatetimeIndex(
        pd.Series(dates, index=dates).groupby(dates.to_period("M")).max().to_numpy()
    )


def build_alpha_dataset(
    price: pd.DataFrame,
    volume: pd.DataFrame,
    base_config: dict[str, Any],
    alpha_config: dict[str, Any],
    membership: pd.DataFrame,
    *,
    include_unlabeled: bool = False,
) -> AlphaDataset:
    """Build month-end point-in-time features and a beta-adjusted return target."""
    price = price.sort_index().astype(float)
    volume = volume.reindex(index=price.index, columns=price.columns).astype(float)
    member = membership.reindex_like(price).fillna(False).astype(bool)
    returns = price.pct_change(fill_method=None)

    market_daily = returns.where(member).mean(axis=1, skipna=True)
    market_index = (1.0 + market_daily.fillna(0.0)).cumprod()
    beta_lookback = int(alpha_config["target"]["beta_lookback_days"])
    minimum_beta_periods = round(beta_lookback * 2.0 / 3.0)
    market_variance = market_daily.rolling(
        beta_lookback, min_periods=minimum_beta_periods
    ).var()
    beta = returns.rolling(beta_lookback, min_periods=minimum_beta_periods).cov(
        market_daily
    ).div(market_variance, axis=0)
    correlation = returns.rolling(beta_lookback, min_periods=minimum_beta_periods).corr(
        market_daily
    )

    momentum_12_1 = price.shift(21).div(price.shift(252)).sub(1.0)
    momentum_6_1 = price.shift(21).div(price.shift(126)).sub(1.0)
    momentum_3_1 = price.shift(21).div(price.shift(63)).sub(1.0)
    return_1m = price.div(price.shift(21)).sub(1.0)
    market_momentum_12_1 = market_index.shift(21).div(market_index.shift(252)).sub(1.0)
    market_momentum_6_1 = market_index.shift(21).div(market_index.shift(126)).sub(1.0)
    residual_momentum_12_1 = momentum_12_1.sub(beta.mul(market_momentum_12_1, axis=0))
    residual_momentum_6_1 = momentum_6_1.sub(beta.mul(market_momentum_6_1, axis=0))

    volatility_20 = returns.rolling(20, min_periods=15).std() * np.sqrt(252.0)
    volatility_60 = returns.rolling(60, min_periods=40).std() * np.sqrt(252.0)
    idiosyncratic_volatility = volatility_60.mul(
        np.sqrt((1.0 - correlation.pow(2)).clip(lower=0.0))
    )
    skewness_60 = returns.rolling(60, min_periods=40).skew()
    trailing_drawdown_120 = price.div(
        price.rolling(120, min_periods=80).max()
    ).sub(1.0)

    log_volume = np.log(volume.where(volume > 0.0))
    volume_surprise_20 = log_volume.sub(log_volume.rolling(20, min_periods=15).mean()).div(
        log_volume.rolling(20, min_periods=15).std()
    )
    volume_mean_20 = volume.rolling(20, min_periods=15).mean()
    volume_mean_60 = volume.rolling(60, min_periods=40).mean()
    dollar_volume_20 = price.mul(volume).rolling(20, min_periods=15).mean()
    amihud_60 = (
        returns.abs()
        .div(price.mul(volume).where(lambda values: values > 0.0))
        .rolling(60, min_periods=40)
        .mean()
    )

    stock_features = {
        "momentum_12_1": momentum_12_1,
        "momentum_6_1": momentum_6_1,
        "momentum_3_1": momentum_3_1,
        "return_1m": return_1m,
        "momentum_acceleration": momentum_3_1.sub(momentum_6_1),
        "residual_momentum_12_1": residual_momentum_12_1,
        "residual_momentum_6_1": residual_momentum_6_1,
        "volatility_20": volatility_20,
        "volatility_60": volatility_60,
        "idiosyncratic_volatility_126": idiosyncratic_volatility,
        "beta_126": beta,
        "skewness_60": skewness_60,
        "trailing_drawdown_120": trailing_drawdown_120,
        "volume_surprise_20": volume_surprise_20,
        "volume_trend_20_60": volume_mean_20.div(volume_mean_60).sub(1.0),
        "log_dollar_volume_20": np.log(dollar_volume_20.where(dollar_volume_20 > 0.0)),
        "amihud_illiquidity_60": amihud_60,
    }
    ranked = {f"rank_{name}": _rank(values, member) for name, values in stock_features.items()}

    market_return_1m = market_index.div(market_index.shift(21)).sub(1.0)
    market_return_3m = market_index.div(market_index.shift(63)).sub(1.0)
    market_volatility_20 = market_daily.rolling(20, min_periods=15).std() * np.sqrt(252.0)
    member_return_1m = return_1m.where(member)
    regime_features = {
        "market_return_1m": market_return_1m,
        "market_return_3m": market_return_3m,
        "market_volatility_20": market_volatility_20,
        "market_breadth_1m": member_return_1m.gt(0.0).sum(axis=1).div(
            member_return_1m.notna().sum(axis=1)
        ),
        "cross_sectional_dispersion_1m": member_return_1m.std(axis=1, skipna=True),
    }
    feature_columns = list(ranked) + list(regime_features)

    horizon = int(alpha_config["target"]["horizon_trading_days"])
    future_return = price.shift(-horizon).div(price).sub(1.0)
    future_market_return = market_index.shift(-horizon).div(market_index).sub(1.0)
    future_residual_return = future_return.sub(beta.mul(future_market_return, axis=0))

    universe = alpha_config["universe"]
    eligible = (
        member
        & price.ge(float(universe["minimum_price"]))
        & dollar_volume_20.ge(float(universe["minimum_dollar_volume_20"]))
    )
    signal_dates = month_end_trading_dates(price.index)
    signal_dates = signal_dates[signal_dates >= pd.Timestamp(base_config["splits"]["modern_holdout"]["start"])]
    full_index = pd.MultiIndex.from_product(
        [signal_dates, price.columns], names=["date", "ticker"]
    )
    dataset = pd.DataFrame(index=full_index)
    for name, values in ranked.items():
        dataset[name] = _flatten(values, full_index)
    for name, values in regime_features.items():
        dataset[name] = np.repeat(values.reindex(signal_dates).to_numpy(), len(price.columns))
    dataset["eligible"] = _flatten(eligible.astype(float), full_index).astype(bool)
    dataset["future_return_21"] = _flatten(future_return, full_index)
    dataset["future_market_return_21"] = np.repeat(
        future_market_return.reindex(signal_dates).to_numpy(), len(price.columns)
    )
    dataset["future_residual_return_21"] = _flatten(future_residual_return, full_index)
    dataset["risk_composite"] = dataset[
        [
            "rank_momentum_3_1",
            "rank_volatility_20",
            "rank_beta_126",
            "rank_idiosyncratic_volatility_126",
        ]
    ].mean(axis=1)
    dataset["feature_coverage"] = dataset[feature_columns].notna().sum(axis=1)
    dataset = dataset.reset_index()
    keep = dataset["eligible"] & dataset["feature_coverage"].ge(len(feature_columns) - 2)
    if not include_unlabeled:
        keep &= dataset["future_residual_return_21"].notna()
    dataset = dataset[keep].copy()
    return AlphaDataset(frame=dataset, feature_columns=feature_columns)
