from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def _wide_to_long(
    price: pd.DataFrame,
    volume: pd.DataFrame,
    tickers: list[str],
) -> pd.DataFrame:
    selected = [ticker for ticker in tickers if ticker in price.columns]
    price_long = price[selected].rename_axis("date").stack().rename("legacy_price")
    volume_long = volume[selected].rename_axis("date").stack().rename("legacy_volume")
    return pd.concat([price_long, volume_long], axis=1).reset_index(names=["date", "legacy_ticker"])


def _prepare_provider(
    bars: pd.DataFrame,
    mapping: Mapping[str, str],
    *,
    suffix: str,
) -> pd.DataFrame:
    required = {"date", "ticker", "close", "volume"}
    missing = required - set(bars.columns)
    if missing:
        raise ValueError(f"Provider bars are missing columns: {sorted(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["provider_ticker"] = frame["ticker"].astype(str).str.upper()
    frame["legacy_ticker"] = frame["provider_ticker"].map(mapping)
    frame = frame.dropna(subset=["legacy_ticker"])
    frame = frame.rename(
        columns={
            "close": f"provider_close_{suffix}",
            "volume": f"provider_volume_{suffix}",
        }
    )
    return frame[
        [
            "date",
            "legacy_ticker",
            "provider_ticker",
            f"provider_close_{suffix}",
            f"provider_volume_{suffix}",
        ]
    ]


def _correlation(left: pd.Series, right: pd.Series) -> float:
    valid = pd.concat([left, right], axis=1).dropna()
    if len(valid) < 2 or valid.iloc[:, 0].nunique() < 2 or valid.iloc[:, 1].nunique() < 2:
        return float("nan")
    return float(valid.iloc[:, 0].corr(valid.iloc[:, 1]))


def reconcile_legacy_overlap(
    legacy_price: pd.DataFrame,
    legacy_volume: pd.DataFrame,
    raw_bars: pd.DataFrame,
    adjusted_bars: pd.DataFrame,
    provider_to_legacy: Mapping[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare legacy fields with raw and fully adjusted Alpaca bars."""
    mapping = {str(key).upper(): str(value).upper() for key, value in provider_to_legacy.items()}
    legacy = _wide_to_long(legacy_price, legacy_volume, sorted(set(mapping.values())))
    raw = _prepare_provider(raw_bars, mapping, suffix="raw")
    adjusted = _prepare_provider(adjusted_bars, mapping, suffix="adjusted").drop(
        columns=["provider_ticker"]
    )
    detail = legacy.merge(raw, on=["date", "legacy_ticker"], how="inner").merge(
        adjusted,
        on=["date", "legacy_ticker"],
        how="inner",
    )
    if detail.empty:
        return detail, pd.DataFrame()

    detail = detail.sort_values(["legacy_ticker", "date"]).reset_index(drop=True)
    detail["legacy_return"] = detail.groupby("legacy_ticker")["legacy_price"].pct_change()
    detail["provider_raw_return"] = detail.groupby("legacy_ticker")[
        "provider_close_raw"
    ].pct_change()
    detail["provider_adjusted_return"] = detail.groupby("legacy_ticker")[
        "provider_close_adjusted"
    ].pct_change()
    detail["raw_price_pct_difference"] = detail["provider_close_raw"].div(
        detail["legacy_price"]
    ).sub(1.0)
    detail["adjusted_price_pct_difference"] = detail["provider_close_adjusted"].div(
        detail["legacy_price"]
    ).sub(1.0)
    detail["raw_volume_ratio"] = detail["provider_volume_raw"].div(detail["legacy_volume"])

    rows = []
    for ticker, group in detail.groupby("legacy_ticker"):
        raw_return_error = (group["provider_raw_return"] - group["legacy_return"]).abs()
        adjusted_return_error = (
            group["provider_adjusted_return"] - group["legacy_return"]
        ).abs()
        raw_error = float(raw_return_error.median())
        adjusted_error = float(adjusted_return_error.median())
        best_price_definition = "adjusted" if adjusted_error < raw_error else "raw"
        rows.append(
            {
                "legacy_ticker": ticker,
                "provider_ticker": str(group["provider_ticker"].iloc[0]),
                "overlap_rows": int(len(group)),
                "overlap_start": str(group["date"].min().date()),
                "overlap_end": str(group["date"].max().date()),
                "raw_return_correlation": _correlation(
                    group["legacy_return"], group["provider_raw_return"]
                ),
                "adjusted_return_correlation": _correlation(
                    group["legacy_return"], group["provider_adjusted_return"]
                ),
                "raw_median_absolute_return_difference": raw_error,
                "adjusted_median_absolute_return_difference": adjusted_error,
                "best_price_definition": best_price_definition,
                "raw_median_absolute_price_pct_difference": float(
                    group["raw_price_pct_difference"].abs().median()
                ),
                "adjusted_median_absolute_price_pct_difference": float(
                    group["adjusted_price_pct_difference"].abs().median()
                ),
                "raw_volume_correlation": _correlation(
                    group["legacy_volume"], group["provider_volume_raw"]
                ),
                "raw_median_volume_ratio": float(
                    group["raw_volume_ratio"].replace([np.inf, -np.inf], np.nan).median()
                ),
            }
        )
    summary = pd.DataFrame(rows).sort_values("legacy_ticker").reset_index(drop=True)
    return detail, summary

