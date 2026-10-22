from __future__ import annotations

from typing import Any

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def alpha_model_factories(config: dict[str, Any]) -> dict[str, Pipeline]:
    seed = int(config["project"]["random_seed"])
    ridge = config["models"]["ridge"]
    boosting = config["models"]["hist_gradient_boosting"]
    return {
        "ridge": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=float(ridge["alpha"]))),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
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
