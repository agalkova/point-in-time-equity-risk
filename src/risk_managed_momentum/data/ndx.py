from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import requests

PTDATA_CONSTITUENTS_URL = "https://api.ptdata.io/v1/index-constituents"


def verify_sha256(path: Path, expected: str) -> None:
    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError(f"SHA-256 mismatch for {path.name}: {observed} != {expected}")


def normalize_sparse_component_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert dated full-roster rows into one row per effective-date/ticker pair."""
    required = {"date", "tickers"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Component history is missing columns: {sorted(missing)}")
    rows = []
    for record in frame.itertuples(index=False):
        effective_date = pd.Timestamp(record.date).normalize()
        tickers = sorted({item.strip().upper() for item in str(record.tickers).split(",") if item.strip()})
        if not 90 <= len(tickers) <= 110:
            raise ValueError(
                f"Implausible Nasdaq-100 roster size {len(tickers)} on {effective_date.date()}"
            )
        rows.extend(
            {"snapshot_date": effective_date, "ticker": ticker}
            for ticker in tickers
        )
    result = pd.DataFrame(rows).drop_duplicates(["snapshot_date", "ticker"])
    return result.sort_values(["snapshot_date", "ticker"]).reset_index(drop=True)


def month_end_snapshot_dates(start: str, end: str) -> pd.DatetimeIndex:
    start_date = pd.Timestamp(start).normalize()
    end_date = pd.Timestamp(end).normalize()
    if start_date > end_date:
        raise ValueError("Snapshot start must not be after end")
    return pd.date_range(start_date, end_date, freq="ME")


def download_ndx_snapshots(
    dates: pd.DatetimeIndex,
    destination: Path,
    *,
    timeout_seconds: float = 30.0,
) -> list[Path]:
    """Download resumable point-in-time NDX snapshots; stop cleanly on daily quota."""
    paths = []
    for snapshot_date in dates:
        path = destination / f"ndx_{snapshot_date.date()}.json"
        if path.exists():
            paths.append(path)
            continue
        response = requests.get(
            PTDATA_CONSTITUENTS_URL,
            params={"index": "NDX", "as_of_date": str(snapshot_date.date())},
            timeout=timeout_seconds,
        )
        if response.status_code == 429:
            cached = len(list(destination.glob("ndx_*.json"))) if destination.exists() else 0
            raise RuntimeError(
                "PtData free quota reached after caching "
                f"{cached} snapshots. Rerun after the UTC daily reset; existing files resume."
            )
        response.raise_for_status()
        payload = response.json()
        if payload.get("index") != "NDX":
            raise ValueError(f"Unexpected index response for {snapshot_date.date()}")
        destination.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
        paths.append(path)
    return paths


def normalize_ndx_snapshots(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        payload = json.loads(path.read_text())
        snapshot_date = pd.Timestamp(payload["as_of_date"]).normalize()
        for constituent in payload.get("constituents", []):
            ticker = str(constituent.get("ticker", "")).strip().upper()
            if ticker:
                rows.append(
                    {
                        "snapshot_date": snapshot_date,
                        "ticker": ticker,
                        "cik": constituent.get("cik"),
                        "name": constituent.get("name"),
                    }
                )
    if not rows:
        raise ValueError("No Nasdaq-100 constituents were returned")
    frame = pd.DataFrame(rows).drop_duplicates(["snapshot_date", "ticker"])
    identity_counts = frame.dropna(subset=["cik"]).groupby("ticker")["cik"].nunique()
    reused = identity_counts[identity_counts > 1]
    if not reused.empty:
        raise ValueError(f"Ticker-to-CIK identity changed in NDX snapshots: {reused.to_dict()}")
    return frame.sort_values(["snapshot_date", "ticker"]).reset_index(drop=True)


def expand_monthly_membership(
    snapshots: pd.DataFrame,
    *,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Forward-fill each month-end roster until the next observed snapshot."""
    frame = snapshots.copy()
    frame["snapshot_date"] = pd.to_datetime(frame["snapshot_date"]).dt.normalize()
    rosters = {
        date: sorted(group["ticker"].unique())
        for date, group in frame.groupby("snapshot_date")
    }
    dates = pd.bdate_range(start, end)
    snapshot_dates = pd.DatetimeIndex(sorted(rosters))
    rows = []
    for day in dates:
        eligible = snapshot_dates[snapshot_dates <= day]
        if eligible.empty:
            continue
        source_date = eligible[-1]
        rows.extend(
            {"date": day, "ticker": ticker, "snapshot_date": source_date}
            for ticker in rosters[source_date]
        )
    return pd.DataFrame(rows)
