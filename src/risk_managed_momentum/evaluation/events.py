from __future__ import annotations

import pandas as pd


def thin_non_overlapping_signals(
    frame: pd.DataFrame,
    *,
    horizon_days: int,
) -> pd.DataFrame:
    """Greedily retain signals whose forward windows do not overlap per security."""
    if horizon_days <= 0:
        raise ValueError("Horizon must be positive")
    work = frame.sort_values(["ticker", "date"]).copy()
    unique_dates = pd.Index(sorted(pd.to_datetime(work["date"]).unique()))
    ordinal = {date: index for index, date in enumerate(unique_dates)}
    keep = []
    for _, group in work.groupby("ticker", sort=False):
        last_ordinal = -horizon_days - 1
        for index, row in group.iterrows():
            current = ordinal[pd.Timestamp(row["date"])]
            if current > last_ordinal + horizon_days:
                keep.append(index)
                last_ordinal = current
    return work.loc[keep].sort_values(["date", "ticker"]).reset_index(drop=True)


def warning_metrics(
    frame: pd.DataFrame,
    *,
    score_column: str,
    warning_percentile: float,
    warning_column: str | None = None,
) -> dict[str, float | int]:
    if not 0.0 < warning_percentile < 1.0:
        raise ValueError("Warning percentile must lie between zero and one")
    work = frame.dropna(subset=[score_column, "target"]).copy()
    if warning_column is None:
        cutoff = work.groupby("date")[score_column].transform(
            lambda values: values.quantile(warning_percentile)
        )
        warning = work[score_column] >= cutoff
    else:
        warning = work[warning_column].astype(bool)
    event = work["target"].astype(bool)
    true_positive = warning & event
    false_positive = warning & ~event
    lead = work.loc[true_positive, "first_breach_days"].dropna()
    return {
        "observations": len(work),
        "warnings": int(warning.sum()),
        "events": int(event.sum()),
        "recall": float(true_positive.sum() / event.sum()) if event.any() else float("nan"),
        "precision": float(true_positive.sum() / warning.sum()) if warning.any() else float("nan"),
        "false_warning_rate": float(false_positive.sum() / (~event).sum())
        if (~event).any()
        else float("nan"),
        "median_lead_days": float(lead.median()) if not lead.empty else float("nan"),
        "mean_lead_days": float(lead.mean()) if not lead.empty else float("nan"),
    }
