from __future__ import annotations

import numpy as np
import pandas as pd

FUNDAMENTAL_FEATURES = [
    "fundamental_roa",
    "fundamental_gross_profitability",
    "fundamental_operating_profitability",
    "fundamental_cash_return_on_assets",
    "fundamental_accruals",
    "fundamental_leverage",
    "fundamental_revenue_growth",
    "fundamental_asset_growth",
]


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.where(denominator.abs() > 1e-12))


def build_filing_features(annual_facts: pd.DataFrame) -> pd.DataFrame:
    """Create annual fundamental signals attached to their public filing dates."""
    required = {"ticker", "end", "filed", "assets"}
    missing = required.difference(annual_facts.columns)
    if missing:
        raise ValueError(f"Annual facts missing required columns: {sorted(missing)}")
    frame = annual_facts.copy()
    frame["end"] = pd.to_datetime(frame["end"]).dt.normalize()
    frame["filed"] = pd.to_datetime(frame["filed"]).dt.normalize()
    frame = frame.sort_values(["ticker", "end", "filed"])
    # Use the latest statement for each fiscal period when calculating growth. The final
    # as-of expansion below still prevents any later filing from entering an earlier date.
    latest_period = frame.drop_duplicates(["ticker", "end"], keep="last").copy()
    grouped = latest_period.groupby("ticker", group_keys=False)
    prior_assets = grouped["assets"].shift(1)
    prior_revenue = grouped["revenue"].shift(1) if "revenue" in frame else np.nan

    latest_period["fundamental_roa"] = _safe_ratio(
        latest_period.get("net_income", pd.Series(index=latest_period.index, dtype=float)),
        latest_period["assets"],
    )
    latest_period["fundamental_gross_profitability"] = _safe_ratio(
        latest_period.get("gross_profit", pd.Series(index=latest_period.index, dtype=float)),
        latest_period["assets"],
    )
    latest_period["fundamental_operating_profitability"] = _safe_ratio(
        latest_period.get("operating_income", pd.Series(index=latest_period.index, dtype=float)),
        latest_period["assets"],
    )
    latest_period["fundamental_cash_return_on_assets"] = _safe_ratio(
        latest_period.get(
            "operating_cash_flow", pd.Series(index=latest_period.index, dtype=float)
        ),
        latest_period["assets"],
    )
    latest_period["fundamental_accruals"] = _safe_ratio(
        latest_period.get("net_income", pd.Series(index=latest_period.index, dtype=float))
        - latest_period.get(
            "operating_cash_flow", pd.Series(index=latest_period.index, dtype=float)
        ),
        latest_period["assets"],
    )
    latest_period["fundamental_leverage"] = _safe_ratio(
        latest_period.get("liabilities", pd.Series(index=latest_period.index, dtype=float)),
        latest_period["assets"],
    )
    latest_period["fundamental_revenue_growth"] = _safe_ratio(
        latest_period.get("revenue", pd.Series(index=latest_period.index, dtype=float)),
        prior_revenue,
    ).sub(1.0)
    latest_period["fundamental_asset_growth"] = _safe_ratio(
        latest_period["assets"], prior_assets
    ).sub(1.0)
    return latest_period[["ticker", "end", "filed", *FUNDAMENTAL_FEATURES]].copy()


def point_in_time_fundamentals(
    filing_features: pd.DataFrame,
    signal_frame: pd.DataFrame,
) -> pd.DataFrame:
    """As-of join each stock/date to the latest financial statement filed by then."""
    left = signal_frame[["date", "ticker"]].copy()
    left["date"] = pd.to_datetime(left["date"]).dt.normalize()
    right = filing_features.copy()
    right["filed"] = pd.to_datetime(right["filed"]).dt.normalize()
    pieces = []
    for ticker, signals in left.groupby("ticker", sort=False):
        facts = right[right["ticker"].eq(ticker)].drop(columns="ticker")
        signals = signals.sort_values("date")
        if facts.empty:
            empty = signals.copy()
            for column in ["end", "filed", *FUNDAMENTAL_FEATURES]:
                empty[column] = pd.NaT if column in {"end", "filed"} else np.nan
            pieces.append(empty)
            continue
        pieces.append(
            pd.merge_asof(
                signals,
                facts.sort_values("filed"),
                left_on="date",
                right_on="filed",
                direction="backward",
                allow_exact_matches=True,
            )
        )
    joined = pd.concat(pieces, ignore_index=True)
    if (joined["filed"] > joined["date"]).fillna(False).any():
        raise AssertionError("Point-in-time join leaked a filing published after the signal date")
    return joined


def add_cross_sectional_fundamental_ranks(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    output = frame.copy()
    rank_columns = []
    # Accruals, leverage, and asset growth are conventionally preferable when lower.
    lower_is_better = {
        "fundamental_accruals",
        "fundamental_leverage",
        "fundamental_asset_growth",
    }
    for feature in FUNDAMENTAL_FEATURES:
        rank_name = f"rank_{feature}"
        rank = output.groupby("date")[feature].rank(method="average", pct=True)
        output[rank_name] = 1.0 - rank if feature in lower_is_better else rank
        rank_columns.append(rank_name)
    return output, rank_columns
