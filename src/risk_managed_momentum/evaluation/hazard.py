from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def risk_strata(frame: pd.DataFrame, score_column: str, strata: int) -> pd.Series:
    count = min(int(strata), len(frame))
    if count < 2:
        return pd.Series(1, index=frame.index, dtype=int)
    ranked = frame[score_column].rank(method="first")
    return pd.qcut(ranked, q=count, labels=False).astype(int).add(1)


def episode_score_summary(
    frame: pd.DataFrame,
    *,
    target_column: str,
    score_column: str,
    horizon: int,
    strata: int,
) -> dict[str, float | int]:
    target = frame[target_column].astype(int)
    score = frame[score_column].astype(float)
    prevalence = float(target.mean())
    average_precision = float(average_precision_score(target, score))
    groups = risk_strata(frame, score_column, strata)
    event_rates = target.groupby(groups).mean()
    bottom = float(event_rates.iloc[0])
    top = float(event_rates.iloc[-1])
    high_risk_events = frame.loc[(groups == groups.max()) & target.eq(1), "first_breach_days"]
    return {
        "episodes": len(frame),
        "events": int(target.sum()),
        "prevalence": prevalence,
        "roc_auc": float(roc_auc_score(target, score)),
        "average_precision": average_precision,
        "average_precision_lift": average_precision / prevalence if prevalence else np.nan,
        "brier_score": float(brier_score_loss(target, score)),
        "top_stratum_event_rate": top,
        "bottom_stratum_event_rate": bottom,
        "top_minus_bottom_event_rate": top - bottom,
        "top_to_bottom_risk_ratio": top / bottom if bottom else np.nan,
        "median_lead_time_days_top_stratum_events": (
            float(high_risk_events.median()) if len(high_risk_events) else np.nan
        ),
        "horizon_days": int(horizon),
    }


def calibration_by_stratum(
    frame: pd.DataFrame,
    *,
    universe: str,
    horizon: int,
    score_column: str,
    target_column: str,
    strata: int,
) -> pd.DataFrame:
    groups = risk_strata(frame, score_column, strata)
    return (
        frame.assign(risk_stratum=groups)
        .groupby("risk_stratum")
        .agg(
            episodes=(target_column, "size"),
            mean_predicted_risk=(score_column, "mean"),
            observed_event_rate=(target_column, "mean"),
        )
        .reset_index()
        .assign(universe=universe, horizon_days=int(horizon))
    )

