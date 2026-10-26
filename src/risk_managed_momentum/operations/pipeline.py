from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import FittedHazardModel, predict_cumulative_risk
from risk_managed_momentum.operations.monitoring import build_health_report


@dataclass(frozen=True)
class RiskPipelineResult:
    signals: pd.DataFrame
    health: dict[str, Any]
    scored_episodes: pd.DataFrame
    feature_columns: list[str]


def score_and_monitor(
    *,
    price: pd.DataFrame,
    volume: pd.DataFrame,
    membership: pd.DataFrame,
    requested_as_of: pd.Timestamp,
    market_data_date: pd.Timestamp,
    model: FittedHazardModel,
    base_config: dict[str, Any],
    hazard_config: dict[str, Any],
    operations_config: dict[str, Any],
) -> RiskPipelineResult:
    """Build live episodes, score a frozen model, and apply operational gates."""
    live = build_exuberance_episode_dataset(
        price,
        volume,
        base_config,
        hazard_config,
        membership=membership,
        include_unlabeled=True,
    )
    if live.feature_columns != model.feature_columns:
        raise RuntimeError("Production feature schema differs from the frozen training schema")
    scored = predict_cumulative_risk(model, live.frame)
    reference_config = operations_config["monitoring_reference"]
    reference = scored[
        scored["date"].between(reference_config["start"], reference_config["end"])
    ].copy()
    if reference.empty:
        raise RuntimeError("No episodes exist in the frozen monitoring reference window")
    recent_cutoff = market_data_date - pd.Timedelta(
        days=int(operations_config["pipeline"]["recent_monitoring_calendar_days"])
    )
    recent = scored[scored["date"].ge(recent_cutoff)].copy()
    health = build_health_report(
        requested_as_of=requested_as_of,
        market_data_date=market_data_date,
        price=price,
        membership=membership,
        reference_episodes=reference,
        recent_episodes=recent,
        feature_columns=live.feature_columns,
        score_column="risk_40",
        quality_config=operations_config["quality_gates"],
        drift_config=operations_config["drift"],
    )
    signal_columns = [
        "date",
        "ticker",
        "risk_10",
        "risk_20",
        "risk_40",
        "risk_60",
        "rank_ret_60",
        "rank_volatility_20",
        "rank_volume_z_20",
        "market_return_20",
        "market_breadth_20",
    ]
    signals = scored[scored["date"].eq(market_data_date)][signal_columns].copy()
    signals = signals.sort_values(["risk_40", "ticker"], ascending=[False, True])
    if not health["signals_authorized"]:
        signals = signals.iloc[0:0].copy()
    return RiskPipelineResult(
        signals=signals,
        health=health,
        scored_episodes=scored,
        feature_columns=live.feature_columns,
    )
