from __future__ import annotations

from typing import Any

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def advanced_model_factories(config: dict[str, Any]) -> dict[str, Pipeline]:
    seed = int(config["project"]["random_seed"])
    logistic = config["models"]["logistic"]
    boosting = config["models"]["hist_gradient_boosting"]
    return {
        "logistic": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=float(logistic["c"]), max_iter=1000, random_state=seed
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=float(boosting["learning_rate"]),
                        max_iter=int(boosting["max_iter"]),
                        max_leaf_nodes=int(boosting["max_leaf_nodes"]),
                        min_samples_leaf=int(boosting["min_samples_leaf"]),
                        l2_regularization=float(boosting["l2_regularization"]),
                        random_state=seed,
                    ),
                ),
            ]
        ),
    }
