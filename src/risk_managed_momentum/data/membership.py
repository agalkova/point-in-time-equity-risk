from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Iterable

import pandas as pd
import requests


WIKIPEDIA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKIPEDIA_SP500_HISTORY_URL = (
    "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
)


@dataclass(frozen=True)
class MembershipSource:
    current: pd.DataFrame
    changes: pd.DataFrame


def normalize_symbol(value: object) -> str | None:
    if pd.isna(value):
        return None
    symbol = str(value).strip().upper()
    return symbol or None


def _flatten_column(column: object) -> str:
    if isinstance(column, tuple):
        return " ".join(str(part).strip() for part in column if str(part) != "nan").strip()
    return str(column).strip()


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.columns = [_flatten_column(column) for column in result.columns]
    return result


def parse_wikipedia_tables(tables: Iterable[pd.DataFrame]) -> MembershipSource:
    flattened = [_flatten_columns(table) for table in tables]
    current = next(
        (table for table in flattened if {"Symbol", "Security", "CIK"}.issubset(table.columns)),
        None,
    )
    changes = next(
        (
            table
            for table in flattened
            if ("Date Date" in table.columns or "Effective Date Effective Date" in table.columns)
            and "Added Ticker" in table.columns
            and "Removed Ticker" in table.columns
        ),
        None,
    )
    if current is None or changes is None:
        available = [list(table.columns) for table in flattened]
        raise ValueError(f"Could not identify S&P 500 tables; found columns: {available}")

    current = current.rename(
        columns={
            "Symbol": "ticker",
            "Security": "security",
            "GICS Sector": "sector",
            "GICS Sub-Industry": "sub_industry",
            "CIK": "cik",
        }
    )
    current["ticker"] = current["ticker"].map(normalize_symbol)
    current = current.dropna(subset=["ticker"]).drop_duplicates("ticker")

    changes = changes.rename(
        columns={
            "Date Date": "date",
            "Effective Date Effective Date": "date",
            "Added Ticker": "added_ticker",
            "Added Security": "added_security",
            "Removed Ticker": "removed_ticker",
            "Removed Security": "removed_security",
            "Reason Reason": "reason",
        }
    )
    changes["date"] = pd.to_datetime(changes["date"], errors="raise").dt.normalize()
    for column in ["added_ticker", "removed_ticker"]:
        changes[column] = changes[column].map(normalize_symbol)
    return MembershipSource(current=current, changes=changes.sort_values("date"))


def fetch_wikipedia_membership(
    *,
    current_url: str = WIKIPEDIA_SP500_URL,
    history_url: str = WIKIPEDIA_SP500_HISTORY_URL,
    timeout_seconds: float = 30.0,
) -> MembershipSource:
    tables: list[pd.DataFrame] = []
    for url in [current_url, history_url]:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": "risk-managed-momentum/0.1.0 (research project)"},
        )
        response.raise_for_status()
        tables.extend(pd.read_html(StringIO(response.text)))
    return parse_wikipedia_tables(tables)


def symbols_needed_for_period(
    source: MembershipSource,
    *,
    start: str | pd.Timestamp,
) -> list[str]:
    start_date = pd.Timestamp(start).normalize()
    relevant = source.changes[source.changes["date"] >= start_date]
    values: set[str] = set(source.current["ticker"].dropna())
    values.update(relevant["added_ticker"].dropna())
    values.update(relevant["removed_ticker"].dropna())
    return sorted(values)


def _present_symbol(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def daily_membership(
    source: MembershipSource,
    *,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.DataFrame:
    """Reconstruct weekday membership by reversing the published change log."""
    start_date = pd.Timestamp(start).normalize()
    end_date = pd.Timestamp(end).normalize()
    if start_date > end_date:
        raise ValueError("Membership start must not be after end")

    members = set(source.current["ticker"].dropna())
    changes = source.changes.sort_values("date", ascending=False)

    # Move the current membership snapshot back to the requested end date.
    for row in changes[changes["date"] > end_date].itertuples(index=False):
        added = _present_symbol(row.added_ticker)
        removed = _present_symbol(row.removed_ticker)
        if added:
            members.discard(added)
        if removed:
            members.add(removed)

    by_date = {date: group for date, group in changes.groupby("date", sort=False)}
    frames: list[pd.DataFrame] = []
    for day in reversed(pd.bdate_range(start_date, end_date)):
        frames.append(pd.DataFrame({"date": day, "ticker": sorted(members)}))
        if day in by_date:
            for row in by_date[day].itertuples(index=False):
                added = _present_symbol(row.added_ticker)
                removed = _present_symbol(row.removed_ticker)
                if added:
                    members.discard(added)
                if removed:
                    members.add(removed)

    if not frames:
        return pd.DataFrame(columns=["date", "ticker"])
    return pd.concat(reversed(frames), ignore_index=True)
