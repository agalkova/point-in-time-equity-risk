from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests

PTDATA_URL = "https://api.ptdata.io/v1/fundamentals"
PTDATA_METRICS = (
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "weighted_avg_shares_diluted",
    "eps_diluted",
)


def _request_one(
    ticker: str,
    fiscal_year: int,
    destination: Path,
    *,
    as_of_date: date,
    timeout_seconds: float = 30.0,
) -> Path:
    if destination.exists():
        return destination
    provider_ticker = ticker.replace(".", "-")
    params: list[tuple[str, str | int]] = [
        ("ticker", provider_ticker),
        ("as_of_date", as_of_date.isoformat()),
        ("fiscal_year", fiscal_year),
        ("fiscal_period", "FY"),
        *[("metrics", metric) for metric in PTDATA_METRICS],
    ]
    for attempt in range(4):
        response = requests.get(PTDATA_URL, params=params, timeout=timeout_seconds)
        if response.status_code == 429 and attempt < 3:
            delay = min(float(response.headers.get("Retry-After", "2")), 30.0)
            time.sleep(delay)
            continue
        response.raise_for_status()
        payload = response.json()
        if str(payload.get("ticker", "")).upper() != provider_ticker.upper():
            raise ValueError(
                f"Ticker mismatch: requested {provider_ticker}, received {payload.get('ticker')}"
            )
        payload["_requested_ticker"] = ticker
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
        return destination
    raise RuntimeError(f"Rate-limit retries exhausted for {ticker} FY{fiscal_year}")


def download_ptdata_history(
    tickers: list[str],
    destination: Path,
    *,
    first_fiscal_year: int = 2018,
    last_fiscal_year: int = 2025,
    workers: int = 3,
) -> list[Path]:
    """Download a resumable point-in-time annual pilot within the provider's free quota."""
    today = date.today()
    jobs = []
    for ticker in tickers:
        for fiscal_year in range(first_fiscal_year, last_fiscal_year + 1):
            # Query the latest version available by the end of the following year, capped at
            # today. Each returned metric still carries its actual knowledge date.
            as_of = min(date(fiscal_year + 1, 12, 31), today)
            path = destination / f"{ticker}_{fiscal_year}.json"
            jobs.append((ticker, fiscal_year, path, as_of))
    paths: list[Path] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _request_one,
                ticker,
                fiscal_year,
                path,
                as_of_date=as_of,
            ): (ticker, fiscal_year)
            for ticker, fiscal_year, path, as_of in jobs
        }
        for future in as_completed(futures):
            paths.append(future.result())
    return sorted(paths)


def normalize_ptdata_files(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text())
        metrics = payload.get("metrics", {})
        if not metrics:
            continue
        fiscal_years = {int(value["fiscal_year"]) for value in metrics.values()}
        if len(fiscal_years) != 1:
            raise ValueError(f"Mixed fiscal years in {path}")
        knowledge_dates = [pd.Timestamp(value["knowledge_from"]).normalize() for value in metrics.values()]
        accessions = {str(value["source_accession"]) for value in metrics.values()}
        row: dict[str, Any] = {
            "ticker": str(payload.get("_requested_ticker", payload["ticker"])).upper(),
            "fiscal_year": fiscal_years.pop(),
            # Use the latest component knowledge date: all row values were public by then.
            "filed": max(knowledge_dates),
            "end": pd.NaT,
            "accession": "|".join(sorted(accessions)),
            "provider": "ptdata",
        }
        for metric in PTDATA_METRICS:
            item = metrics.get(metric)
            row[metric] = float(item["value"]) if item is not None else None
        rows.append(row)
    if not rows:
        raise ValueError("No usable point-in-time fundamental records were downloaded")
    return (
        pd.DataFrame(rows)
        .sort_values(["ticker", "fiscal_year", "filed"])
        .drop_duplicates(["ticker", "fiscal_year"], keep="last")
        .reset_index(drop=True)
    )
