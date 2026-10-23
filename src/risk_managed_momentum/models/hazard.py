from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def interval_columns(horizons: Sequence[int]) -> list[str]:
    return [f"interval_after_{int(end)}" for end in horizons[:-1]]


def expand_hazard_training_rows(
    episodes: pd.DataFrame,
    feature_columns: Sequence[str],
    horizons: Sequence[int],
) -> pd.DataFrame:
    """Expand episodes into interval rows, stopping after the first event."""
    rows = []
    starts = [1, *[int(value) + 1 for value in horizons[:-1]]]
    indicators = interval_columns(horizons)
    for interval_index, (start, end) in enumerate(zip(starts, horizons)):
        breach = episodes["first_breach_days"]
        at_risk = breach.isna() | breach.ge(start)
        part = episodes.loc[at_risk, list(feature_columns)].copy()
        part["hazard_event"] = breach.loc[at_risk].between(start, int(end)).astype(int)
        for indicator_index, name in enumerate(indicators, start=1):
            part[name] = float(interval_index == indicator_index)
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


@dataclass(frozen=True)
class FittedHazardModel:
    pipeline: Pipeline
    feature_columns: list[str]
    horizons: list[int]
    interval_feature_columns: list[str]


def fit_hazard_model(
    episodes: pd.DataFrame,
    feature_columns: Sequence[str],
    horizons: Sequence[int],
    *,
    c: float,
    maximum_iterations: int,
    random_seed: int,
) -> FittedHazardModel:
    horizons = [int(value) for value in horizons]
    interval_features = interval_columns(horizons)
    design_columns = [*feature_columns, *interval_features]
    training = expand_hazard_training_rows(episodes, feature_columns, horizons)
    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=float(c),
                    max_iter=int(maximum_iterations),
                    random_state=int(random_seed),
                ),
            ),
        ]
    )
    pipeline.fit(training[design_columns], training["hazard_event"])
    return FittedHazardModel(
        pipeline=pipeline,
        feature_columns=list(feature_columns),
        horizons=horizons,
        interval_feature_columns=interval_features,
    )


def predict_cumulative_risk(
    fitted: FittedHazardModel,
    episodes: pd.DataFrame,
) -> pd.DataFrame:
    """Return interval hazards and monotonic cumulative event probabilities."""
    design_columns = [*fitted.feature_columns, *fitted.interval_feature_columns]
    output = episodes.copy().reset_index(drop=True)
    survival = np.ones(len(output), dtype=float)
    for interval_index, horizon in enumerate(fitted.horizons):
        design = output[fitted.feature_columns].copy()
        for indicator_index, name in enumerate(fitted.interval_feature_columns, start=1):
            design[name] = float(interval_index == indicator_index)
        hazard = fitted.pipeline.predict_proba(design[design_columns])[:, 1]
        output[f"hazard_{horizon}"] = hazard
        survival *= 1.0 - hazard
        output[f"risk_{horizon}"] = 1.0 - survival
    return output


def standardized_coefficients(fitted: FittedHazardModel) -> pd.DataFrame:
    names = [*fitted.feature_columns, *fitted.interval_feature_columns]
    values = fitted.pipeline.named_steps["model"].coef_[0]
    return (
        pd.DataFrame({"feature": names, "standardized_coefficient": values})
        .assign(absolute_coefficient=lambda frame: frame["standardized_coefficient"].abs())
        .sort_values("absolute_coefficient", ascending=False)
        .reset_index(drop=True)
    )

