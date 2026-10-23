from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pandas as pd

from risk_managed_momentum.features.advanced import build_advanced_research_dataset


@dataclass(frozen=True)
class EpisodeDataset:
    frame: pd.DataFrame
    feature_columns: list[str]


def exuberance_onsets(
    price: pd.DataFrame,
    membership: pd.DataFrame,
    *,
    runup_lookback_days: int,
    minimum_runup: float,
    peak_lookback_days: int,
    maximum_distance_below_peak: float,
    washout_trading_days: int,
) -> pd.DataFrame:
    """Identify first eligible dates after a fixed non-eligible washout."""
    runup = price.div(price.shift(runup_lookback_days)).sub(1.0)
    distance_below_peak = price.div(
        price.rolling(peak_lookback_days, min_periods=peak_lookback_days).max()
    ).sub(1.0)
    eligible = (
        runup.ge(minimum_runup)
        & distance_below_peak.ge(maximum_distance_below_peak)
        & membership
    )
    recently_eligible = (
        eligible.shift(1)
        .rolling(washout_trading_days, min_periods=1)
        .max()
        .fillna(0.0)
        .astype(bool)
    )
    return eligible & ~recently_eligible


def build_exuberance_episode_dataset(
    price: pd.DataFrame,
    volume: pd.DataFrame,
    base_config: dict[str, Any],
    hazard_config: dict[str, Any],
    membership: pd.DataFrame | None = None,
    *,
    include_unlabeled: bool = False,
) -> EpisodeDataset:
    """Build one row per exuberance onset with a complete forward outcome window."""
    price = price.sort_index().astype(float)
    volume = volume.reindex(index=price.index, columns=price.columns).astype(float)
    member = (
        price.notna()
        if membership is None
        else membership.reindex(index=price.index, columns=price.columns).fillna(False).astype(bool)
    )
    episode = hazard_config["episode"]
    outcome = hazard_config["outcome"]
    onsets = exuberance_onsets(
        price,
        member,
        runup_lookback_days=int(episode["runup_lookback_days"]),
        minimum_runup=float(episode["minimum_runup"]),
        peak_lookback_days=int(episode["peak_lookback_days"]),
        maximum_distance_below_peak=float(episode["maximum_distance_below_peak"]),
        washout_trading_days=int(episode["washout_trading_days"]),
    )

    feature_config = deepcopy(base_config)
    feature_config["eligibility"] = {
        "runup_lookback_days": int(episode["runup_lookback_days"]),
        "minimum_runup": float(episode["minimum_runup"]),
        "peak_lookback_days": int(episode["peak_lookback_days"]),
        "maximum_distance_below_peak": float(episode["maximum_distance_below_peak"]),
    }
    feature_config["target"] = {
        "horizon_days": int(outcome["maximum_horizon_days"]),
        "drawdown_threshold": float(outcome["drawdown_threshold"]),
    }
    advanced = build_advanced_research_dataset(
        price,
        volume,
        feature_config,
        membership=member,
        include_unlabeled=include_unlabeled,
    )

    onset_pairs = (
        onsets.rename_axis("date")
        .rename_axis("ticker", axis=1)
        .stack()
        .rename("episode_onset")
        .reset_index()
    )
    onset_pairs = onset_pairs[onset_pairs["episode_onset"]].drop(columns="episode_onset")
    frame = advanced.frame.merge(
        onset_pairs, on=["date", "ticker"], how="inner", validate="one_to_one"
    )
    frame = frame.rename(
        columns={
            "target": "target_60",
            "future_min_return": "future_min_return_60",
            "drawdown_severity": "drawdown_severity_60",
        }
    )
    first_breach = frame["first_breach_days"]
    for horizon in hazard_config["outcome"]["horizon_end_days"]:
        frame[f"target_{int(horizon)}"] = first_breach.le(int(horizon)).astype(int)
        if include_unlabeled:
            frame[f"target_{int(horizon)}"] = frame[f"target_{int(horizon)}"].mask(
                frame["future_min_return_60"].isna(), pd.NA
            ).astype("Int64")
    frame["episode_id"] = (
        frame["ticker"].astype(str) + "_" + frame["date"].dt.strftime("%Y%m%d")
    )
    return EpisodeDataset(
        frame=frame.sort_values(["date", "ticker"]).reset_index(drop=True),
        feature_columns=advanced.feature_columns,
    )

