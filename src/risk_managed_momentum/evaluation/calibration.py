from __future__ import annotations

import numpy as np
import pandas as pd


def calibration_table(
    target: pd.Series,
    score: pd.Series | np.ndarray,
    *,
    bins: int = 10,
) -> pd.DataFrame:
    if bins < 2:
        raise ValueError("Calibration requires at least two bins")
    frame = pd.DataFrame({"target": target.to_numpy(), "score": np.asarray(score)}).dropna()
    ranks = frame["score"].rank(method="first")
    frame["bin"] = pd.qcut(ranks, bins, labels=False).astype(int) + 1
    return (
        frame.groupby("bin")
        .agg(observations=("target", "size"), mean_score=("score", "mean"), event_rate=("target", "mean"))
        .reset_index()
    )


def expected_calibration_error(table: pd.DataFrame) -> float:
    total = float(table["observations"].sum())
    if total == 0.0:
        return float("nan")
    error = table["mean_score"].sub(table["event_rate"]).abs()
    return float((error * table["observations"]).sum() / total)
