from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


def _metric(name: str) -> Callable[[np.ndarray, np.ndarray], float]:
    if name == "roc_auc":
        return lambda target, score: float(roc_auc_score(target, score))
    if name == "average_precision_lift":
        return lambda target, score: float(average_precision_score(target, score) / target.mean())
    raise ValueError(f"Unsupported paired-bootstrap metric: {name}")


def paired_date_block_bootstrap(
    frame: pd.DataFrame,
    *,
    target_column: str,
    first_score_column: str,
    second_score_column: str,
    metric_names: tuple[str, ...] = ("roc_auc", "average_precision_lift"),
    block_length: int,
    iterations: int,
    random_seed: int,
) -> pd.DataFrame:
    """Bootstrap paired score differences while keeping same-date episodes together."""
    dates = pd.Index(sorted(pd.to_datetime(frame["date"]).unique()))
    if len(dates) < 2:
        raise ValueError("Paired bootstrap requires at least two episode dates")
    block = min(int(block_length), len(dates))
    starts = np.arange(len(dates) - block + 1)
    rng = np.random.default_rng(random_seed)
    samples: dict[str, list[float]] = {name: [] for name in metric_names}
    draws_needed = int(np.ceil(len(dates) / block))
    by_date = {date: group for date, group in frame.groupby(pd.to_datetime(frame["date"]))}

    for _ in range(int(iterations)):
        sampled_dates: list[pd.Timestamp] = []
        for start in rng.choice(starts, size=draws_needed, replace=True):
            sampled_dates.extend(pd.Timestamp(value) for value in dates[start : start + block])
        pieces = [by_date[date] for date in sampled_dates[: len(dates)]]
        sample = pd.concat(pieces, ignore_index=True)
        target = sample[target_column].to_numpy(dtype=int)
        if np.unique(target).size < 2:
            continue
        first = sample[first_score_column].to_numpy(dtype=float)
        second = sample[second_score_column].to_numpy(dtype=float)
        for name in metric_names:
            function = _metric(name)
            samples[name].append(function(target, second) - function(target, first))

    rows = []
    for name, values in samples.items():
        array = np.asarray(values, dtype=float)
        if array.size == 0:
            raise ValueError(f"No valid bootstrap samples for {name}")
        rows.append(
            {
                "metric": name,
                "challenger_minus_champion": float(array.mean()),
                "ci_lower_95": float(np.quantile(array, 0.025)),
                "ci_upper_95": float(np.quantile(array, 0.975)),
                "probability_difference_above_zero": float(np.mean(array > 0.0)),
                "valid_iterations": int(array.size),
            }
        )
    return pd.DataFrame(rows)
