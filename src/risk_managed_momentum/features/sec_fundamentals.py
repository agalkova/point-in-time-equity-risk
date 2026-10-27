from __future__ import annotations

import numpy as np
import pandas as pd

FUNDAMENTAL_FEATURES = [
    "gross_margin",
    "operating_margin",
    "cash_flow_margin",
    "net_margin",
    "return_on_assets",
    "liabilities_to_assets",
    "equity_to_assets",
    "cash_flow_to_assets",
    "asset_growth",
    "revenue_growth",
]

LOWER_IS_BETTER = {"liabilities_to_assets", "asset_growth"}


def _date(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, utc=True, errors="coerce").dt.tz_convert(None).dt.normalize()


def assign_point_in_time_cik(
    signals: pd.DataFrame,
    identity_intervals: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the issuer CIK whose membership interval contains each signal date."""
    required_signals = {"date", "ticker"}
    required_intervals = {"ticker", "valid_from", "valid_to", "cik", "status"}
    if missing := required_signals.difference(signals.columns):
        raise ValueError(f"Signals missing required columns: {sorted(missing)}")
    if missing := required_intervals.difference(identity_intervals.columns):
        raise ValueError(f"Identity intervals missing required columns: {sorted(missing)}")

    left = signals.copy().reset_index(drop=True)
    left["date"] = _date(left["date"])
    left["_signal_row"] = np.arange(len(left))
    intervals = identity_intervals.copy()
    intervals["valid_from"] = _date(intervals["valid_from"])
    intervals["valid_to"] = _date(intervals["valid_to"])
    keep = [
        "ticker",
        "valid_from",
        "valid_to",
        "cik",
        "status",
        "identity_source",
        "confidence",
    ]
    keep = [column for column in keep if column in intervals]
    candidates = left[["_signal_row", "date", "ticker"]].merge(
        intervals[keep], on="ticker", how="left"
    )
    valid = candidates[
        candidates["date"].ge(candidates["valid_from"])
        & candidates["date"].le(candidates["valid_to"])
    ].copy()
    duplicates = valid["_signal_row"].duplicated(keep=False)
    if duplicates.any():
        rows = valid.loc[duplicates, ["date", "ticker"]].drop_duplicates().head(5)
        raise ValueError(f"Multiple identity intervals matched a signal: {rows.to_dict('records')}")

    identity_columns = [column for column in keep if column != "ticker"]
    output = left.merge(
        valid[["_signal_row", *identity_columns]],
        on="_signal_row",
        how="left",
        validate="one_to_one",
    )
    output["cik"] = pd.to_numeric(output["cik"], errors="coerce").astype("Int64")
    return output.drop(columns="_signal_row")


def canonicalize_annual_filings(annual: pd.DataFrame) -> pd.DataFrame:
    """Choose one deterministic issuer filing when several share a filing date."""
    required = {"cik", "filed", "period", "adsh", "fundamental_schema"}
    if missing := required.difference(annual.columns):
        raise ValueError(f"Annual filings missing required columns: {sorted(missing)}")
    output = annual.copy()
    output["cik"] = pd.to_numeric(output["cik"], errors="coerce").astype("Int64")
    output["filed"] = _date(output["filed"])
    output["period"] = _date(output["period"])
    output = output.dropna(subset=["cik", "filed"]).sort_values(
        ["cik", "filed", "period", "adsh"], kind="mergesort"
    )
    return output.drop_duplicates(["cik", "filed"], keep="last").reset_index(drop=True)


def point_in_time_filing_join(
    signals_with_cik: pd.DataFrame,
    annual_filings: pd.DataFrame,
    *,
    maximum_filing_age_days: int = 550,
) -> pd.DataFrame:
    """Join the latest already-public filing to each signal, then expire stale filings."""
    if maximum_filing_age_days <= 0:
        raise ValueError("maximum_filing_age_days must be positive")
    signals = signals_with_cik.copy().reset_index(drop=True)
    signals["date"] = _date(signals["date"])
    signals["_signal_row"] = np.arange(len(signals))
    filings = canonicalize_annual_filings(annual_filings)
    filing_columns = [column for column in filings.columns if column != "cik"]

    pieces: list[pd.DataFrame] = []
    for cik, group in signals.dropna(subset=["cik"]).groupby("cik", sort=False):
        issuer_filings = filings[filings["cik"].eq(cik)].drop(columns="cik")
        ordered = group.sort_values("date")
        if issuer_filings.empty:
            joined = ordered.copy()
            for column in filing_columns:
                joined[column] = pd.NaT if column in {"filed", "period"} else np.nan
        else:
            joined = pd.merge_asof(
                ordered,
                issuer_filings.sort_values("filed"),
                left_on="date",
                right_on="filed",
                direction="backward",
                allow_exact_matches=True,
            )
        pieces.append(joined)

    unresolved = signals[signals["cik"].isna()].copy()
    for column in filing_columns:
        unresolved[column] = pd.NaT if column in {"filed", "period"} else np.nan
    pieces.append(unresolved)
    output = pd.concat(pieces, ignore_index=True).sort_values("_signal_row")
    output["filing_age_days"] = (output["date"] - output["filed"]).dt.days
    output["filing_is_stale"] = output["filing_age_days"].gt(maximum_filing_age_days)
    stale = output["filing_is_stale"].fillna(False)
    output.loc[stale, filing_columns] = np.nan
    output.loc[stale, "filing_age_days"] = np.nan
    if (output["filed"] > output["date"]).fillna(False).any():
        raise AssertionError("Point-in-time join leaked a filing published after the signal date")
    return output.drop(columns="_signal_row").reset_index(drop=True)


def add_accounting_group_ranks(
    frame: pd.DataFrame,
    *,
    minimum_quality_features: int = 4,
) -> tuple[pd.DataFrame, list[str]]:
    """Rank available ratios within date and accounting schema without pre-rank filling."""
    output = frame.copy()
    group_keys = ["date", "fundamental_schema"]
    rank_columns: list[str] = []
    quality_parts: list[str] = []
    for feature in FUNDAMENTAL_FEATURES:
        availability = f"available_{feature}"
        rank_name = f"fundamental_rank_{feature}"
        quality_name = f"_quality_{feature}"
        output[availability] = output[feature].notna().astype(float)
        output[rank_name] = output.groupby(group_keys, dropna=False)[feature].rank(
            method="average", pct=True
        )
        output[quality_name] = (
            1.0 - output[rank_name] if feature in LOWER_IS_BETTER else output[rank_name]
        )
        rank_columns.append(rank_name)
        quality_parts.append(quality_name)

    output["fundamental_feature_count"] = output[FUNDAMENTAL_FEATURES].notna().sum(axis=1)
    output["fundamental_quality_score"] = output[quality_parts].mean(axis=1, skipna=True)
    output.loc[
        output["fundamental_feature_count"].lt(minimum_quality_features),
        "fundamental_quality_score",
    ] = np.nan
    output["fundamental_schema_financials"] = output["fundamental_schema"].eq(
        "financials_v1"
    ).astype(float)
    output["fundamental_schema_real_estate"] = output["fundamental_schema"].eq(
        "real_estate_v1"
    ).astype(float)
    return output.drop(columns=quality_parts), rank_columns
