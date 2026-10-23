from __future__ import annotations

import re

import pandas as pd

VALID_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]*$")


def build_event_sourced_snapshots(
    seed: pd.DataFrame,
    changes: pd.DataFrame,
    *,
    start: str,
    end: str,
) -> pd.DataFrame:
    required_seed = {"effective_date", "ticker"}
    required_changes = {"date", "action", "ticker"}
    if missing := required_seed.difference(seed.columns):
        raise ValueError(f"Seed is missing columns: {sorted(missing)}")
    if missing := required_changes.difference(changes.columns):
        raise ValueError(f"Changes are missing columns: {sorted(missing)}")

    seed = seed.copy()
    changes = changes.copy()
    seed["effective_date"] = pd.to_datetime(seed["effective_date"]).dt.normalize()
    changes["date"] = pd.to_datetime(changes["date"]).dt.normalize()
    seed["ticker"] = seed["ticker"].astype(str).str.strip().str.upper()
    changes["ticker"] = changes["ticker"].astype(str).str.strip().str.upper()
    invalid = sorted(
        ticker
        for ticker in set(seed["ticker"]) | set(changes["ticker"])
        if not VALID_TICKER.fullmatch(ticker)
    )
    if invalid:
        raise ValueError(f"Invalid ticker-like source values: {invalid}")
    if seed["effective_date"].nunique() != 1:
        raise ValueError("Seed must contain exactly one effective date")
    if not set(changes["action"]).issubset({"added", "removed"}):
        raise ValueError("Changes contain an unsupported action")

    start_date = pd.Timestamp(start).normalize()
    end_date = pd.Timestamp(end).normalize()
    if start_date > end_date:
        raise ValueError("Start must not follow end")
    roster = set(seed["ticker"])
    ordered = changes.sort_values(
        ["date", "action", "ticker"],
        key=lambda column: column.map({"removed": 0, "added": 1})
        if column.name == "action"
        else column,
    )
    for row in ordered[ordered["date"].le(start_date)].itertuples(index=False):
        if row.action == "removed":
            roster.discard(row.ticker)
        else:
            roster.add(row.ticker)

    rows = []

    def record(date: pd.Timestamp) -> None:
        if not 350 <= len(roster) <= 450:
            raise ValueError(f"Implausible S&P 400 roster size {len(roster)} on {date.date()}")
        rows.extend({"snapshot_date": date, "ticker": ticker} for ticker in sorted(roster))

    record(start_date)
    in_window = ordered[ordered["date"].gt(start_date) & ordered["date"].le(end_date)]
    for date, group in in_window.groupby("date", sort=True):
        for row in group.itertuples(index=False):
            if row.action == "removed":
                roster.discard(row.ticker)
            else:
                roster.add(row.ticker)
        record(pd.Timestamp(date))
    return pd.DataFrame(rows)


def roster_jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0
