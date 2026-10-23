from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit, logit
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from risk_managed_momentum.evaluation.calibration import (
    calibration_table,
    expected_calibration_error,
)


def intercept_adjustment(probability: np.ndarray, outcome: np.ndarray) -> float:
    """Fit a fixed-slope logistic recalibration intercept."""
    probability = np.clip(np.asarray(probability, dtype=float), 1e-8, 1.0 - 1e-8)
    outcome = np.asarray(outcome, dtype=float)
    target = float(np.clip(outcome.mean(), 1e-8, 1.0 - 1e-8))
    base_logit = logit(probability)
    objective = lambda delta: float(expit(base_logit + delta).mean() - target)
    return float(brentq(objective, -30.0, 30.0))


def interval_observations(
    scored_episodes: pd.DataFrame,
    horizons: Sequence[int],
) -> tuple[np.ndarray, np.ndarray]:
    probabilities = []
    outcomes = []
    starts = [1, *[int(value) + 1 for value in horizons[:-1]]]
    breach = scored_episodes["first_breach_days"]
    for start, end in zip(starts, horizons):
        at_risk = breach.isna() | breach.ge(start)
        probabilities.append(scored_episodes.loc[at_risk, f"hazard_{int(end)}"].to_numpy())
        outcomes.append(breach.loc[at_risk].between(start, int(end)).astype(int).to_numpy())
    return np.concatenate(probabilities), np.concatenate(outcomes)


def walk_forward_intercept_recalibration(
    scored_episodes: pd.DataFrame,
    horizons: Sequence[int],
    *,
    first_year: int,
    last_year: int,
    maturity_buffer_calendar_days: int,
    minimum_prior_episodes: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply annual intercept updates using only fully matured prior episodes."""
    outputs = []
    audit_rows = []
    for year in range(int(first_year), int(last_year) + 1):
        cutoff = pd.Timestamp(year=year, month=1, day=1) - pd.Timedelta(
            days=int(maturity_buffer_calendar_days)
        )
        history = scored_episodes[scored_episodes["date"].le(cutoff)]
        test = scored_episodes[scored_episodes["date"].dt.year.eq(year)].copy()
        if test.empty:
            continue
        if len(history) >= int(minimum_prior_episodes):
            probability, outcome = interval_observations(history, horizons)
            delta = intercept_adjustment(probability, outcome)
        else:
            probability = np.array([], dtype=float)
            outcome = np.array([], dtype=float)
            delta = 0.0
        survival = np.ones(len(test), dtype=float)
        for horizon in horizons:
            adjusted_hazard = expit(
                logit(np.clip(test[f"hazard_{int(horizon)}"], 1e-8, 1.0 - 1e-8)) + delta
            )
            test[f"calibrated_hazard_{int(horizon)}"] = adjusted_hazard
            survival *= 1.0 - adjusted_hazard
            test[f"calibrated_risk_{int(horizon)}"] = 1.0 - survival
        test["calibration_delta"] = delta
        outputs.append(test)
        audit_rows.append(
            {
                "year": year,
                "maturity_cutoff": cutoff,
                "prior_episodes": len(history),
                "prior_interval_rows": len(outcome),
                "prior_interval_event_rate": float(outcome.mean()) if len(outcome) else np.nan,
                "intercept_adjustment": delta,
            }
        )
    return pd.concat(outputs, ignore_index=True), pd.DataFrame(audit_rows)


def probability_summary(
    frame: pd.DataFrame,
    *,
    target_column: str,
    score_column: str,
) -> dict[str, float | int]:
    target = frame[target_column].astype(int)
    score = frame[score_column].astype(float).clip(1e-8, 1.0 - 1e-8)
    table = calibration_table(target, score)
    prevalence = float(target.mean())
    average_precision = float(average_precision_score(target, score))
    return {
        "observations": len(frame),
        "events": int(target.sum()),
        "prevalence": prevalence,
        "mean_predicted_risk": float(score.mean()),
        "roc_auc": float(roc_auc_score(target, score)),
        "average_precision": average_precision,
        "average_precision_lift": average_precision / prevalence,
        "brier_score": float(brier_score_loss(target, score)),
        "log_loss": float(log_loss(target, score)),
        "expected_calibration_error": expected_calibration_error(table),
    }

