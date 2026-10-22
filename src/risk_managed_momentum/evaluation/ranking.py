from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def classification_metrics(target: pd.Series, score: np.ndarray) -> dict[str, float | int]:
    prevalence = float(target.mean())
    average_precision = float(average_precision_score(target, score))
    return {
        "observations": int(len(target)),
        "positives": int(target.sum()),
        "prevalence": prevalence,
        "average_precision": average_precision,
        "average_precision_lift": average_precision / prevalence if prevalence else float("nan"),
        "roc_auc": float(roc_auc_score(target, score)),
        "brier_score": float(brier_score_loss(target, score)),
    }


def add_daily_deciles(frame: pd.DataFrame, score_column: str) -> pd.Series:
    def one_day(values: pd.Series) -> pd.Series:
        if values.notna().sum() < 10:
            return pd.Series(np.nan, index=values.index)
        ranks = values.rank(method="first")
        return pd.qcut(ranks, 10, labels=False).astype(float).add(1.0)

    return frame.groupby("date", group_keys=False)[score_column].apply(one_day)


def daily_rank_ic(frame: pd.DataFrame, score_column: str) -> pd.Series:
    values: dict[pd.Timestamp, float] = {}
    for date, group in frame.groupby("date"):
        valid = group[[score_column, "drawdown_severity"]].dropna()
        if len(valid) >= 10 and valid.nunique().min() > 1:
            values[date] = float(
                spearmanr(valid[score_column], valid["drawdown_severity"]).statistic
            )
    return pd.Series(values, name="rank_ic").sort_index()


def moving_block_interval(
    values: pd.Series,
    *,
    block_length: int,
    iterations: int,
    random_seed: int,
) -> tuple[float, float]:
    clean = values.dropna().to_numpy()
    if len(clean) == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(random_seed)
    effective_block = min(block_length, len(clean))
    blocks_needed = int(np.ceil(len(clean) / effective_block))
    max_start = len(clean) - effective_block
    sample_means = []
    for _ in range(iterations):
        starts = rng.integers(0, max_start + 1, size=blocks_needed)
        sample = np.concatenate(
            [clean[start : start + effective_block] for start in starts]
        )[: len(clean)]
        sample_means.append(float(sample.mean()))
    return tuple(float(value) for value in np.quantile(sample_means, [0.025, 0.975]))


def decile_table(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    work = frame.copy()
    work["risk_decile"] = add_daily_deciles(work, score_column)
    work = work.dropna(subset=["risk_decile"]).copy()
    work["risk_decile"] = work["risk_decile"].astype(int)
    return (
        work.groupby("risk_decile")
        .agg(
            observations=("target", "size"),
            event_rate=("target", "mean"),
            mean_future_min_return=("future_min_return", "mean"),
            median_future_min_return=("future_min_return", "median"),
            mean_score=(score_column, "mean"),
        )
        .reset_index()
    )

