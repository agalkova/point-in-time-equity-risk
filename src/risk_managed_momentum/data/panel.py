from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd


BAR_COLUMNS = ["date", "ticker", "close", "volume"]


def build_point_in_time_panel(
    bars: pd.DataFrame,
    membership: pd.DataFrame,
    aliases: Iterable[Mapping[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return adjusted close, volume, and a point-in-time membership mask."""
    missing_bar_columns = set(BAR_COLUMNS) - set(bars.columns)
    if missing_bar_columns:
        raise ValueError(f"Bars missing columns: {sorted(missing_bar_columns)}")
    if not {"date", "ticker"}.issubset(membership.columns):
        raise ValueError("Membership must contain date and ticker")

    bars = bars[BAR_COLUMNS].copy()
    bars["date"] = pd.to_datetime(bars["date"]).dt.normalize()
    bars["ticker"] = bars["ticker"].astype(str).str.upper()
    bars = bars.sort_values(["ticker", "date"]).drop_duplicates(["date", "ticker"], keep="last")

    membership = membership[["date", "ticker"]].copy()
    membership["date"] = pd.to_datetime(membership["date"]).dt.normalize()
    membership["ticker"] = membership["ticker"].astype(str).str.upper()

    trading_dates = pd.Index(sorted(bars["date"].unique()), name="date")
    membership = membership[membership["date"].isin(trading_dates)].copy()
    membership["provider_ticker"] = membership["ticker"]
    for row in aliases:
        start = pd.Timestamp(str(row["start"])).normalize()
        end = pd.Timestamp(str(row["end"])).normalize()
        mask = (
            membership["ticker"].eq(str(row["membership_ticker"]).upper())
            & membership["date"].between(start, end)
        )
        membership.loc[mask, "provider_ticker"] = str(row["provider_ticker"]).upper()

    joined = membership.merge(
        bars,
        left_on=["date", "provider_ticker"],
        right_on=["date", "ticker"],
        how="left",
        suffixes=("_membership", "_provider"),
        validate="one_to_one",
    )
    joined = joined.rename(columns={"ticker_membership": "ticker"})

    tickers = sorted(membership["ticker"].unique())
    price = joined.pivot(index="date", columns="ticker", values="close").reindex(
        index=trading_dates, columns=tickers
    )
    volume = joined.pivot(index="date", columns="ticker", values="volume").reindex(
        index=trading_dates, columns=tickers
    )
    member = (
        membership.assign(is_member=True)
        .pivot(index="date", columns="ticker", values="is_member")
        .reindex(index=trading_dates, columns=tickers, fill_value=False)
        .fillna(False)
        .astype(bool)
    )
    return price, volume, member


def coverage_summary(price: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker in membership.columns:
        expected = membership[ticker]
        expected_days = int(expected.sum())
        covered_days = int((price[ticker].notna() & expected).sum())
        rows.append(
            {
                "ticker": ticker,
                "membership_trading_days": expected_days,
                "covered_days": covered_days,
                "coverage_rate": covered_days / expected_days if expected_days else float("nan"),
            }
        )
    return pd.DataFrame(rows).sort_values(["coverage_rate", "ticker"]).reset_index(drop=True)
