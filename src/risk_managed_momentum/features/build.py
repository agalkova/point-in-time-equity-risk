from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from risk_managed_momentum.features.targets import future_min_return


@dataclass(frozen=True)
class ResearchDataset:
    frame: pd.DataFrame
    feature_columns: list[str]


def _rank(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rank(axis=1, method="average", pct=True)


def _flatten(frame: pd.DataFrame, index: pd.MultiIndex) -> np.ndarray:
    dates = index.levels[0]
    tickers = index.levels[1]
    aligned = frame.reindex(index=dates, columns=tickers)
    return aligned.to_numpy().reshape(-1)


def build_research_dataset(
    price: pd.DataFrame,
    volume: pd.DataFrame,
    config: dict[str, Any],
    membership: pd.DataFrame | None = None,
    *,
    include_unlabeled: bool = False,
) -> ResearchDataset:
    """Build the frozen v0.1 cross-sectional research table."""
    price = price.sort_index().astype(float)
    volume = volume.reindex(index=price.index, columns=price.columns).astype(float)
    if membership is None:
        membership = price.notna()
    else:
        membership = (
            membership.reindex(index=price.index, columns=price.columns, fill_value=False)
            .fillna(False)
            .astype(bool)
        )
    returns = price.pct_change(fill_method=None)

    ret5 = price.div(price.shift(5)).sub(1.0)
    ret20 = price.div(price.shift(20)).sub(1.0)
    ret60 = price.div(price.shift(60)).sub(1.0)
    ret120 = price.div(price.shift(120)).sub(1.0)
    vol20 = returns.rolling(20, min_periods=15).std() * np.sqrt(252.0)
    vol60 = returns.rolling(60, min_periods=40).std() * np.sqrt(252.0)
    drawdown20 = price.div(price.rolling(20, min_periods=15).max()).sub(1.0)
    drawdown60 = price.div(price.rolling(60, min_periods=50).max()).sub(1.0)

    market_daily = returns.where(membership).mean(axis=1, skipna=True)
    market_index = (1.0 + market_daily.fillna(0.0)).cumprod()
    market_ret20 = market_index.div(market_index.shift(20)).sub(1.0)
    market_ret60 = market_index.div(market_index.shift(60)).sub(1.0)
    market_vol20 = market_daily.rolling(20, min_periods=15).std() * np.sqrt(252.0)
    market_var60 = market_daily.rolling(60, min_periods=40).var()
    member_ret20 = ret20.where(membership)
    market_breadth20 = member_ret20.gt(0.0).sum(axis=1).div(member_ret20.notna().sum(axis=1))
    cross_sectional_dispersion20 = member_ret20.std(axis=1, skipna=True)

    beta60 = returns.rolling(60, min_periods=40).cov(market_daily).div(market_var60, axis=0)
    corr60 = returns.rolling(60, min_periods=40).corr(market_daily)
    idio_vol60 = vol60.mul(np.sqrt((1.0 - corr60.pow(2)).clip(lower=0.0)))

    log_volume = np.log(volume.where(volume > 0.0))
    log_volume_mean20 = log_volume.rolling(20, min_periods=15).mean()
    log_volume_std20 = log_volume.rolling(20, min_periods=15).std()
    volume_z20 = log_volume.sub(log_volume_mean20).div(log_volume_std20)
    volume_mean20 = volume.rolling(20, min_periods=15).mean()
    volume_mean60 = volume.rolling(60, min_periods=40).mean()
    dollar_volume_mean20 = price.mul(volume).rolling(20, min_periods=15).mean()

    stock_features = {
        "ret_5": ret5,
        "ret_20": ret20,
        "ret_60": ret60,
        "ret_120": ret120,
        "volatility_20": vol20,
        "volatility_60": vol60,
        "volatility_ratio_20_60": vol20.div(vol60),
        "drawdown_20": drawdown20,
        "drawdown_60": drawdown60,
        "trend_acceleration": ret20.sub(ret60.div(3.0)),
        "volume_z_20": volume_z20,
        "volume_trend_20_60": volume_mean20.div(volume_mean60).sub(1.0),
        "beta_60": beta60,
        "idiosyncratic_volatility_60": idio_vol60,
        "log_dollar_volume_20": np.log(dollar_volume_mean20.where(dollar_volume_mean20 > 0.0)),
    }
    ranked_features = {
        f"rank_{name}": _rank(value.where(membership)) for name, value in stock_features.items()
    }
    regime_features = {
        "market_return_20": market_ret20,
        "market_return_60": market_ret60,
        "market_volatility_20": market_vol20,
        "market_breadth_20": market_breadth20,
        "cross_sectional_dispersion_20": cross_sectional_dispersion20,
    }
    feature_columns = list(ranked_features) + list(regime_features)

    eligibility_config = config["eligibility"]
    eligibility = (
        ret60.ge(float(eligibility_config["minimum_runup"]))
        & drawdown60.ge(float(eligibility_config["maximum_distance_below_peak"]))
        & membership
    )
    target_config = config["target"]
    horizon = int(target_config["horizon_days"])
    threshold = float(target_config["drawdown_threshold"])
    forward_return = future_min_return(price, horizon)
    next_day_return = price.shift(-1).div(price).sub(1.0)

    full_index = pd.MultiIndex.from_product(
        [price.index, price.columns], names=["date", "ticker"]
    )
    dataset = pd.DataFrame(index=full_index)
    for name, feature in ranked_features.items():
        dataset[name] = _flatten(feature, full_index)
    for name, feature in regime_features.items():
        dataset[name] = np.repeat(feature.reindex(price.index).to_numpy(), len(price.columns))
    dataset["eligible"] = _flatten(eligibility.astype(float), full_index).astype(bool)
    dataset["future_min_return"] = _flatten(forward_return, full_index)
    dataset["drawdown_severity"] = (-dataset["future_min_return"]).clip(lower=0.0)
    dataset["target"] = dataset["future_min_return"].le(threshold).astype(int)
    if include_unlabeled:
        dataset["target"] = dataset["target"].mask(
            dataset["future_min_return"].isna(), pd.NA
        ).astype("Int64")
    dataset["next_day_return"] = _flatten(next_day_return, full_index)
    dataset["feature_coverage"] = dataset[feature_columns].notna().sum(axis=1)
    dataset = dataset.reset_index()
    keep = dataset["eligible"] & dataset["feature_coverage"].ge(len(feature_columns) - 2)
    if not include_unlabeled:
        keep &= dataset["future_min_return"].notna()
    dataset = dataset[keep].copy()
    return ResearchDataset(frame=dataset, feature_columns=feature_columns)


def split_research_dataset(
    dataset: ResearchDataset,
    config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    frame = dataset.frame
    return {
        name: frame[frame["date"].between(values["start"], values["end"])].copy()
        for name, values in {
            "train": config["splits"]["train"],
            "validation": config["splits"]["validation"],
            "legacy_test": config["splits"]["legacy_test"],
        }.items()
    }

