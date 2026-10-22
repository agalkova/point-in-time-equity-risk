from __future__ import annotations

import numpy as np
import pandas as pd

FUNDAMENTAL_FEATURES = [
    "fundamental_gross_margin",
    "fundamental_operating_margin",
    "fundamental_net_margin",
    "fundamental_cash_conversion",
    "fundamental_accrual_ratio",
    "fundamental_revenue_growth",
    "fundamental_gross_profit_growth",
    "fundamental_operating_income_growth",
    "fundamental_cash_flow_growth",
    "fundamental_share_dilution",
]


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.where(denominator.abs() > 1e-12))


def _symmetric_growth(current: pd.Series, previous: pd.Series) -> pd.Series:
    scale = current.abs().add(previous.abs()).div(2.0)
    return current.sub(previous).div(scale.where(scale > 1e-12))


def build_filing_features(annual_facts: pd.DataFrame) -> pd.DataFrame:
    """Create annual fundamental signals attached to their public filing dates."""
    required = {"ticker", "filed", "fiscal_year", "revenue"}
    missing = required.difference(annual_facts.columns)
    if missing:
        raise ValueError(f"Annual facts missing required columns: {sorted(missing)}")
    frame = annual_facts.copy()
    if "end" not in frame:
        frame["end"] = pd.NaT
    frame["end"] = pd.to_datetime(frame["end"], utc=True).dt.tz_convert(None).dt.normalize()
    frame["filed"] = (
        pd.to_datetime(frame["filed"], utc=True).dt.tz_convert(None).dt.normalize()
    )
    frame = frame.sort_values(["ticker", "fiscal_year", "filed"])
    # Use the latest statement for each fiscal period when calculating growth. The final
    # as-of expansion below still prevents any later filing from entering an earlier date.
    latest_period = frame.drop_duplicates(["ticker", "fiscal_year"], keep="last").copy()
    grouped = latest_period.groupby("ticker", group_keys=False)
    prior_revenue = grouped["revenue"].shift(1)
    prior_gross_profit = grouped["gross_profit"].shift(1)
    prior_operating_income = grouped["operating_income"].shift(1)
    prior_cash_flow = grouped["operating_cash_flow"].shift(1)
    prior_shares = grouped["weighted_avg_shares_diluted"].shift(1)

    latest_period["fundamental_gross_margin"] = _safe_ratio(
        latest_period["gross_profit"], latest_period["revenue"]
    )
    latest_period["fundamental_operating_margin"] = _safe_ratio(
        latest_period["operating_income"], latest_period["revenue"]
    )
    latest_period["fundamental_net_margin"] = _safe_ratio(
        latest_period["net_income"], latest_period["revenue"]
    )
    latest_period["fundamental_cash_conversion"] = _safe_ratio(
        latest_period["operating_cash_flow"], latest_period["net_income"].abs()
    )
    latest_period["fundamental_accrual_ratio"] = _safe_ratio(
        latest_period["net_income"].sub(latest_period["operating_cash_flow"]),
        latest_period["revenue"].abs(),
    )
    latest_period["fundamental_revenue_growth"] = _safe_ratio(
        latest_period["revenue"], prior_revenue
    ).sub(1.0)
    latest_period["fundamental_gross_profit_growth"] = _symmetric_growth(
        latest_period["gross_profit"], prior_gross_profit
    )
    latest_period["fundamental_operating_income_growth"] = _symmetric_growth(
        latest_period["operating_income"], prior_operating_income
    )
    latest_period["fundamental_cash_flow_growth"] = _symmetric_growth(
        latest_period["operating_cash_flow"], prior_cash_flow
    )
    latest_period["fundamental_share_dilution"] = _safe_ratio(
        latest_period["weighted_avg_shares_diluted"], prior_shares
    ).sub(1.0)
    return latest_period[
        ["ticker", "fiscal_year", "end", "filed", *FUNDAMENTAL_FEATURES]
    ].copy()


def point_in_time_fundamentals(
    filing_features: pd.DataFrame,
    signal_frame: pd.DataFrame,
) -> pd.DataFrame:
    """As-of join each stock/date to the latest financial statement filed by then."""
    left = signal_frame[["date", "ticker"]].copy()
    left["date"] = pd.to_datetime(left["date"], utc=True).dt.tz_convert(None).dt.normalize()
    right = filing_features.copy()
    right["filed"] = (
        pd.to_datetime(right["filed"], utc=True).dt.tz_convert(None).dt.normalize()
    )
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
    lower_is_better = {"fundamental_accrual_ratio", "fundamental_share_dilution"}
    for feature in FUNDAMENTAL_FEATURES:
        rank_name = f"rank_{feature}"
        rank = output.groupby("date")[feature].rank(method="average", pct=True)
        output[rank_name] = 1.0 - rank if feature in lower_is_better else rank
        rank_columns.append(rank_name)
    return output, rank_columns
