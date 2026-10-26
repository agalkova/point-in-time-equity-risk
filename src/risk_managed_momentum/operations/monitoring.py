from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd


def _finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def population_stability_index(
    reference: Sequence[float],
    current: Sequence[float],
    *,
    bins: int = 10,
) -> float:
    """Quantile-binned PSI with fixed reference breakpoints."""
    reference_array = np.asarray(reference, dtype=float)
    current_array = np.asarray(current, dtype=float)
    reference_array = reference_array[np.isfinite(reference_array)]
    current_array = current_array[np.isfinite(current_array)]
    if len(reference_array) < 2 or len(current_array) < 2:
        return float("nan")
    quantiles = np.linspace(0.0, 1.0, int(bins) + 1)
    edges = np.unique(np.quantile(reference_array, quantiles))
    if len(edges) < 3:
        return 0.0 if np.allclose(reference_array.mean(), current_array.mean()) else float("inf")
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts = np.histogram(reference_array, bins=edges)[0].astype(float)
    current_counts = np.histogram(current_array, bins=edges)[0].astype(float)
    epsilon = 1e-6
    reference_share = np.clip(reference_counts / reference_counts.sum(), epsilon, None)
    current_share = np.clip(current_counts / current_counts.sum(), epsilon, None)
    return float(np.sum((current_share - reference_share) * np.log(current_share / reference_share)))


def build_health_report(
    *,
    requested_as_of: pd.Timestamp,
    market_data_date: pd.Timestamp,
    price: pd.DataFrame,
    membership: pd.DataFrame,
    reference_episodes: pd.DataFrame,
    recent_episodes: pd.DataFrame,
    feature_columns: Sequence[str],
    score_column: str,
    quality_config: dict,
    drift_config: dict,
) -> dict:
    members = membership.loc[market_data_date].astype(bool)
    latest_coverage = float(price.loc[market_data_date, members.index[members]].notna().mean())
    staleness = int((requested_as_of.normalize() - market_data_date.normalize()).days)
    feature_psi = {
        feature: population_stability_index(
            reference_episodes[feature],
            recent_episodes[feature],
            bins=int(drift_config["bins"]),
        )
        for feature in feature_columns
    }
    score_psi = population_stability_index(
        reference_episodes[score_column],
        recent_episodes[score_column],
        bins=int(drift_config["bins"]),
    )
    available_feature_psi = {
        key: value for key, value in feature_psi.items() if not np.isnan(value)
    }
    maximum_feature_psi = max(available_feature_psi.values(), default=float("nan"))
    median_feature_psi = (
        float(np.median(list(available_feature_psi.values())))
        if available_feature_psi
        else float("nan")
    )
    gates = {
        "history_days": {
            "value": len(price),
            "minimum": int(quality_config["minimum_history_trading_days"]),
            "passed": len(price) >= int(quality_config["minimum_history_trading_days"]),
        },
        "latest_membership_price_coverage": {
            "value": latest_coverage,
            "minimum": float(quality_config["minimum_latest_membership_coverage"]),
            "passed": latest_coverage >= float(quality_config["minimum_latest_membership_coverage"]),
        },
        "market_data_staleness_days": {
            "value": staleness,
            "maximum": int(quality_config["maximum_market_data_staleness_calendar_days"]),
            "passed": staleness
            <= int(quality_config["maximum_market_data_staleness_calendar_days"]),
        },
        "recent_episode_count": {
            "value": len(recent_episodes),
            "minimum": int(quality_config["minimum_recent_episodes"]),
            "passed": len(recent_episodes) >= int(quality_config["minimum_recent_episodes"]),
        },
        "drift_metrics_available": {
            "value": not np.isnan(score_psi) and bool(available_feature_psi),
            "required": True,
            "passed": not np.isnan(score_psi) and bool(available_feature_psi),
        },
    }
    failure_threshold = float(drift_config["failure_psi"])
    warning_threshold = float(drift_config["warning_psi"])
    severe_drift = bool(
        (not np.isnan(score_psi) and score_psi > failure_threshold)
        or (not np.isnan(median_feature_psi) and median_feature_psi > failure_threshold)
    )
    warning_drift = bool(
        (not np.isnan(score_psi) and score_psi > warning_threshold)
        or (not np.isnan(maximum_feature_psi) and maximum_feature_psi > warning_threshold)
    )
    hard_gates_passed = all(item["passed"] for item in gates.values())
    status = "FAIL" if not hard_gates_passed or severe_drift else "WARN" if warning_drift else "PASS"
    top_drift = sorted(feature_psi.items(), key=lambda item: np.nan_to_num(item[1], nan=-1.0), reverse=True)[:5]
    return {
        "status": status,
        "signals_authorized": status != "FAIL",
        "requested_as_of": str(requested_as_of.date()),
        "market_data_date": str(market_data_date.date()),
        "gates": gates,
        "drift": {
            "score_psi": _finite_or_none(score_psi),
            "maximum_feature_psi": _finite_or_none(maximum_feature_psi),
            "median_feature_psi": _finite_or_none(median_feature_psi),
            "warning_threshold": warning_threshold,
            "failure_threshold": failure_threshold,
            "top_feature_psi": [
                {"feature": feature, "psi": _finite_or_none(value)}
                for feature, value in top_drift
            ],
        },
    }

