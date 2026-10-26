from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

BAR_COLUMNS = ["date", "ticker", "close", "volume"]


def build_point_in_time_panel(
    bars: pd.DataFrame,
    membership: pd.DataFrame,
    aliases: Iterable[Mapping[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return security histories plus a separate point-in-time membership mask.

    Membership controls eligibility, but it must not truncate prices immediately
    after an index removal: forward outcomes and open positions still require the
    security's subsequent trading history.
    """
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
    tickers = sorted(membership["ticker"].unique())
    provider_price = bars.pivot(index="date", columns="ticker", values="close").reindex(
        index=trading_dates
    )
    provider_volume = bars.pivot(index="date", columns="ticker", values="volume").reindex(
        index=trading_dates
    )
    price = pd.DataFrame(index=trading_dates, columns=tickers, dtype=float)
    volume = pd.DataFrame(index=trading_dates, columns=tickers, dtype=float)
    alias_rows = list(aliases)
    for ticker in tickers:
        ticker_aliases = [
            row
            for row in alias_rows
            if str(row["membership_ticker"]).upper() == str(ticker).upper()
        ]
        reuse_protected = any(
            row.get("download_asof")
            and not row.get("allow_current_series", False)
            and str(row["provider_ticker"]).upper() == ticker
            for row in ticker_aliases
        )
        if ticker in provider_price and not reuse_protected:
            price[ticker] = provider_price[ticker]
            volume[ticker] = provider_volume[ticker]
        for row in ticker_aliases:
            provider = str(row["provider_ticker"]).upper()
            if provider not in provider_price:
                continue
            start = pd.Timestamp(str(row["start"])).normalize()
            end = pd.Timestamp(str(row["end"])).normalize()
            if not row.get("download_asof") and price[ticker].notna().sum() == 0:
                price[ticker] = provider_price[provider]
                volume[ticker] = provider_volume[provider]
            else:
                mask = price.index.to_series().between(start, end).to_numpy()
                price.loc[mask, ticker] = provider_price.loc[mask, provider]
                volume.loc[mask, ticker] = provider_volume.loc[mask, provider]
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
