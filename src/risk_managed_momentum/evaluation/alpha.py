from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

TARGET = "future_residual_return_21"


def monthly_rank_ic(frame: pd.DataFrame, score_column: str) -> pd.Series:
    values: dict[pd.Timestamp, float] = {}
    for date, group in frame.groupby("date"):
        valid = group[[score_column, TARGET]].dropna()
        if len(valid) >= 10 and valid.nunique().min() > 1:
            values[pd.Timestamp(date)] = float(
                spearmanr(valid[score_column], valid[TARGET]).statistic
            )
    return pd.Series(values, name="rank_ic").sort_index()


def alpha_decile_table(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    work = frame.dropna(subset=[score_column, TARGET]).copy()

    def one_month(values: pd.Series) -> pd.Series:
        ranks = values.rank(method="first")
        return pd.qcut(ranks, 10, labels=False).astype(int).add(1)

    work["alpha_decile"] = work.groupby("date", group_keys=False)[score_column].apply(
        one_month
    )
    return (
        work.groupby("alpha_decile")
        .agg(
            observations=(TARGET, "size"),
            mean_future_residual_return=(TARGET, "mean"),
            median_future_residual_return=(TARGET, "median"),
            mean_future_raw_return=("future_return_21", "mean"),
            mean_score=(score_column, "mean"),
        )
        .reset_index()
    )


def alpha_score_summary(frame: pd.DataFrame, score_column: str) -> dict[str, float | int]:
    rank_ic = monthly_rank_ic(frame, score_column)
    deciles = alpha_decile_table(frame, score_column)
    top = float(
        deciles.loc[deciles["alpha_decile"].eq(10), "mean_future_residual_return"].iloc[0]
    )
    bottom = float(
        deciles.loc[deciles["alpha_decile"].eq(1), "mean_future_residual_return"].iloc[0]
    )
    valid = frame[[TARGET, score_column]].dropna()
    return {
        "observations": len(valid),
        "months": int(rank_ic.size),
        "mean_monthly_rank_ic": float(rank_ic.mean()),
        "rank_ic_standard_deviation": float(rank_ic.std(ddof=1)),
        "prediction_target_correlation": float(
            np.corrcoef(valid[score_column], valid[TARGET])[0, 1]
        ),
        "top_decile_mean_residual_return": top,
        "bottom_decile_mean_residual_return": bottom,
        "top_minus_bottom_residual_return": top - bottom,
    }
