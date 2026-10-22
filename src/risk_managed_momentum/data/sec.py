from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# Ordered aliases make tag selection deterministic while accommodating common issuer choices.
ANNUAL_CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
}

FLOW_CONCEPTS = {
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "operating_cash_flow",
}


@dataclass(frozen=True)
class SecDownloadResult:
    ticker: str
    cik: int
    path: Path
    entity_name: str


def download_companyfacts(
    ticker: str,
    cik: int,
    destination: Path,
    *,
    user_agent: str,
    timeout_seconds: float = 30.0,
    session: requests.Session | None = None,
) -> SecDownloadResult:
    """Download one issuer's SEC Companyfacts response without embedding credentials."""
    if "@" not in user_agent:
        raise ValueError("SEC_USER_AGENT must identify the requester and include an email address")
    client = session or requests.Session()
    response = client.get(
        SEC_COMPANYFACTS_URL.format(cik=int(cik)),
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if int(payload.get("cik", -1)) != int(cik):
        raise ValueError(f"CIK mismatch for {ticker}: expected {cik}, received {payload.get('cik')}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    return SecDownloadResult(
        ticker=ticker,
        cik=int(cik),
        path=destination,
        entity_name=str(payload.get("entityName", "")),
    )


def _concept_rows(payload: dict[str, Any], feature_name: str) -> list[dict[str, Any]]:
    us_gaap = payload.get("facts", {}).get("us-gaap", {})
    selected: dict[str, Any] | None = None
    selected_tag = ""
    for tag in ANNUAL_CONCEPTS[feature_name]:
        if tag in us_gaap:
            selected = us_gaap[tag]
            selected_tag = tag
            break
    if selected is None:
        return []

    unit_options = selected.get("units", {})
    units = unit_options.get("USD", [])
    output: list[dict[str, Any]] = []
    for fact in units:
        if fact.get("form") not in {"10-K", "10-K/A"}:
            continue
        if fact.get("fp") != "FY":
            continue
        try:
            end = pd.Timestamp(fact["end"]).normalize()
            filed = pd.Timestamp(fact["filed"]).normalize()
            value = float(fact["val"])
        except (KeyError, TypeError, ValueError):
            continue
        if not pd.notna(end) or not pd.notna(filed) or filed < end:
            continue
        # Retain the issuer's own fiscal-year observation, not older comparative values
        # repeated in a later filing. Most 10-Ks arrive within roughly three months.
        if (filed - end).days > 150:
            continue
        if feature_name in FLOW_CONCEPTS:
            try:
                start = pd.Timestamp(fact["start"]).normalize()
            except (KeyError, TypeError, ValueError):
                continue
            duration = (end - start).days
            if duration < 250 or duration > 450:
                continue
        output.append(
            {
                "concept": feature_name,
                "tag": selected_tag,
                "end": end,
                "filed": filed,
                "accession": str(fact.get("accn", "")),
                "fiscal_year": fact.get("fy"),
                "value": value,
            }
        )
    return output


def normalize_annual_companyfacts(payload: dict[str, Any], ticker: str) -> pd.DataFrame:
    """Return one row per filing/period using only annual, filing-date-stamped facts."""
    rows = []
    for feature_name in ANNUAL_CONCEPTS:
        rows.extend(_concept_rows(payload, feature_name))
    if not rows:
        return pd.DataFrame()
    long = pd.DataFrame(rows)
    long["ticker"] = ticker
    # When amendments or duplicate units exist, retain the last observation reported on
    # a given filing date. The as-of join later decides which filing was known at each signal.
    long = long.sort_values(["filed", "accession"]).drop_duplicates(
        ["ticker", "end", "filed", "concept"], keep="last"
    )
    values = long.pivot_table(
        index=["ticker", "end", "filed", "accession", "fiscal_year"],
        columns="concept",
        values="value",
        aggfunc="last",
    ).reset_index()
    tags = long.pivot_table(
        index=["ticker", "end", "filed", "accession", "fiscal_year"],
        columns="concept",
        values="tag",
        aggfunc="last",
    ).add_prefix("tag_").reset_index()
    return values.merge(
        tags,
        on=["ticker", "end", "filed", "accession", "fiscal_year"],
        how="left",
        validate="one_to_one",
    ).sort_values(["ticker", "filed", "end"])


def normalize_companyfacts_files(paths: Iterable[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        payload = json.loads(path.read_text())
        ticker = path.stem.upper().replace("COMPANYFACTS_", "")
        frame = normalize_annual_companyfacts(payload, ticker)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        raise ValueError("No usable annual SEC facts were found")
    return pd.concat(frames, ignore_index=True).sort_values(["ticker", "filed", "end"])


def download_companyfacts_batch(
    companies: pd.DataFrame,
    destination: Path,
    *,
    user_agent: str,
    request_interval_seconds: float = 0.12,
) -> list[SecDownloadResult]:
    """Download a polite, rate-limited batch from data.sec.gov."""
    results = []
    with requests.Session() as session:
        for row in companies.itertuples(index=False):
            path = destination / f"companyfacts_{row.ticker}.json"
            results.append(
                download_companyfacts(
                    str(row.ticker),
                    int(row.cik),
                    path,
                    user_agent=user_agent,
                    session=session,
                )
            )
            time.sleep(request_interval_seconds)
    return results
