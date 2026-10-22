from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class SelectedModel:
    name: str
    model: Pipeline
    selection_table: pd.DataFrame


def select_logistic_model(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    feature_columns: list[str],
    *,
    random_seed: int = 42,
    c_values: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0),
) -> SelectedModel:
    rows = []
    fitted: dict[str, Pipeline] = {}
    for c_value in c_values:
        name = f"logistic_C_{c_value:g}"
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(C=c_value, max_iter=1000, random_state=random_seed),
                ),
            ]
        )
        model.fit(train[feature_columns], train["target"])
        score = model.predict_proba(validation[feature_columns])[:, 1]
        rows.append(
            {
                "model": name,
                "validation_average_precision": float(
                    average_precision_score(validation["target"], score)
                ),
                "validation_roc_auc": float(roc_auc_score(validation["target"], score)),
            }
        )
        fitted[name] = model
    selection = pd.DataFrame(rows).sort_values(
        ["validation_average_precision", "validation_roc_auc"], ascending=False
    )
    winner = str(selection.iloc[0]["model"])
    return SelectedModel(name=winner, model=fitted[winner], selection_table=selection)

