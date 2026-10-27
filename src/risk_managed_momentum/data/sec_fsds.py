from __future__ import annotations

import os
import subprocess
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

SEC_FSDS_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{period}.zip"

CONCEPT_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "cost_of_revenue": (
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "equity": (
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquity",
    ),
}
FLOW_CONCEPTS = {
    "revenue",
    "gross_profit",
    "cost_of_revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
}
TAG_TO_CONCEPT = {tag: concept for concept, tags in CONCEPT_TAGS.items() for tag in tags}

FUNDAMENTAL_SCHEMAS: dict[str, tuple[str, ...]] = {
    "nonfinancial_v1": (
        "gross_margin",
        "operating_margin",
        "cash_flow_margin",
        "return_on_assets",
        "liabilities_to_assets",
        "asset_growth",
    ),
    "financials_v1": (
        "net_margin",
        "return_on_assets",
        "equity_to_assets",
        "cash_flow_to_assets",
        "revenue_growth",
        "asset_growth",
    ),
    "real_estate_v1": (
        "net_margin",
        "cash_flow_margin",
        "return_on_assets",
        "liabilities_to_assets",
        "revenue_growth",
        "asset_growth",
    ),
}


def _parse_sec_date(values: pd.Series) -> pd.Series:
    """Parse SEC YYYYMMDD fields whether pandas inferred integers or floats."""
    normalized = pd.to_numeric(values, errors="coerce").astype("Int64").astype("string")
    return pd.to_datetime(normalized, format="%Y%m%d", errors="coerce")


def resolve_sec_user_agent(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("SEC_USER_AGENT")
    if not value:
        name = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, check=False
        ).stdout.strip()
        email = subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True, check=False
        ).stdout.strip()
        value = f"{name} {email}".strip()
    if "@" not in value:
        raise ValueError("Provide SEC_USER_AGENT='Name email@example.com' or configure a Git email")
    return value


def download_fsds_archive(
    period: str,
    destination: Path,
    *,
    user_agent: str,
    timeout_seconds: float = 120.0,
) -> Path:
    """Download one official SEC quarterly archive atomically."""
    period = period.lower()
    if len(period) != 6 or period[:4].isdigit() is False or period[4] != "q":
        raise ValueError("SEC period must look like 2024q1")
    if period[5] not in "1234":
        raise ValueError("SEC quarter must be 1 through 4")
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = SEC_FSDS_URL.format(period=period)
    with requests.get(
        url,
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        timeout=timeout_seconds,
        stream=True,
    ) as response:
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    try:
        if not zipfile.is_zipfile(temporary):
            raise ValueError(f"SEC response is not a ZIP archive: {url}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.lower().endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"Expected one {suffix} member, found {matches}")
    return matches[0]


def read_submissions(archive_path: Path, ciks: Iterable[int]) -> pd.DataFrame:
    wanted = {int(value) for value in ciks}
    with (
        zipfile.ZipFile(archive_path) as archive,
        archive.open(_member(archive, "sub.txt")) as handle,
    ):
        frame = pd.read_csv(handle, sep="\t", low_memory=False)
    frame.columns = frame.columns.str.lower()
    frame = frame[
        frame["cik"].astype(int).isin(wanted)
        & frame["form"].isin(["10-K", "10-K/A"])
        & frame["fp"].eq("FY")
    ].copy()
    frame["filed"] = _parse_sec_date(frame["filed"])
    frame["period"] = _parse_sec_date(frame["period"])
    frame = frame.dropna(subset=["filed", "period"])
    return frame[
        ["adsh", "cik", "name", "sic", "form", "period", "fy", "fp", "filed", "instance"]
    ].drop_duplicates("adsh")


def read_relevant_numbers(
    archive_path: Path,
    submissions: pd.DataFrame,
    *,
    chunksize: int = 250_000,
) -> pd.DataFrame:
    accessions = set(submissions["adsh"])
    if not accessions:
        return pd.DataFrame()
    frames = []
    with (
        zipfile.ZipFile(archive_path) as archive,
        archive.open(_member(archive, "num.txt")) as handle,
    ):
        for chunk in pd.read_csv(handle, sep="\t", low_memory=False, chunksize=chunksize):
            chunk.columns = chunk.columns.str.lower()
            keep = (
                chunk["adsh"].isin(accessions)
                & chunk["tag"].isin(TAG_TO_CONCEPT)
                & chunk["uom"].eq("USD")
                & chunk["coreg"].isna()
            )
            if "segments" in chunk:
                keep &= chunk["segments"].isna()
            selected = chunk.loc[
                keep,
                ["adsh", "tag", "version", "ddate", "qtrs", "uom", "value"],
            ].copy()
            if not selected.empty:
                frames.append(selected)
    if not frames:
        return pd.DataFrame()
    numbers = pd.concat(frames, ignore_index=True)
    numbers["ddate"] = _parse_sec_date(numbers["ddate"])
    numbers = numbers.dropna(subset=["ddate"])
    numbers["concept"] = numbers["tag"].map(TAG_TO_CONCEPT)
    return numbers


def _tag_priority(concept: str, tag: str) -> int:
    return CONCEPT_TAGS[concept].index(tag)


def schema_for_sector(sector: str) -> str:
    if sector == "Financials":
        return "financials_v1"
    if sector == "Real Estate":
        return "real_estate_v1"
    return "nonfinancial_v1"


def schema_for_sic(sic: object) -> str:
    """Choose a statement schema when historical GICS data is unavailable."""
    numeric = pd.to_numeric(pd.Series([sic]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "nonfinancial_v1"
    code = int(numeric)
    if 6500 <= code <= 6599 or code == 6798:
        return "real_estate_v1"
    if 6000 <= code <= 6799:
        return "financials_v1"
    return "nonfinancial_v1"


def assign_historical_fundamental_schema(
    frame: pd.DataFrame,
    current_sectors: pd.DataFrame,
) -> pd.DataFrame:
    """Use current GICS when verified and SEC SIC only as a documented schema proxy."""
    sectors = current_sectors[["cik", "sector"]].drop_duplicates("cik")
    result = frame.merge(sectors, on="cik", how="left", validate="many_to_one")
    result["sector_source"] = np.where(result["sector"].notna(), "current_gics", "sec_sic_proxy")
    result["fundamental_schema"] = result["sector"].map(schema_for_sector)
    proxy = result["sector"].isna()
    result.loc[proxy, "fundamental_schema"] = result.loc[proxy, "sic"].map(schema_for_sic)
    result["schema_complete"] = False
    for schema, features in FUNDAMENTAL_SCHEMAS.items():
        mask = result["fundamental_schema"].eq(schema)
        if not mask.any():
            continue
        result.loc[mask, "schema_complete"] = result.loc[mask, list(features)].notna().all(axis=1)
    return result


def assign_fundamental_schema(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["fundamental_schema"] = result["sector"].map(schema_for_sector)
    result["schema_complete"] = False
    for schema, features in FUNDAMENTAL_SCHEMAS.items():
        mask = result["fundamental_schema"].eq(schema)
        if not mask.any():
            continue
        result.loc[mask, "schema_complete"] = result.loc[mask, list(features)].notna().all(axis=1)
    return result


def normalize_annual_filings(
    submissions: pd.DataFrame,
    numbers: pd.DataFrame,
) -> pd.DataFrame:
    """Normalize annual facts with their actual public filing date and source tags."""
    if submissions.empty or numbers.empty:
        return pd.DataFrame()
    merged = numbers.merge(
        submissions[["adsh", "cik", "name", "form", "period", "fy", "filed"]],
        on="adsh",
        how="inner",
        validate="many_to_one",
    )
    merged["priority"] = [
        _tag_priority(concept, tag)
        for concept, tag in zip(merged["concept"], merged["tag"], strict=True)
    ]
    flow = merged[merged["concept"].isin(FLOW_CONCEPTS)].copy()
    flow = flow[flow["qtrs"].eq(4) & flow["ddate"].eq(flow["period"])]
    instant = merged[~merged["concept"].isin(FLOW_CONCEPTS)].copy()
    current_instant = instant[instant["qtrs"].eq(0) & instant["ddate"].eq(instant["period"])]
    prior_assets = instant[
        instant["concept"].eq("assets")
        & instant["qtrs"].eq(0)
        & instant["ddate"].lt(instant["period"])
        & instant["ddate"].ge(instant["period"] - pd.Timedelta(days=450))
    ].copy()
    prior_assets = (
        prior_assets.sort_values(["adsh", "ddate", "priority"])
        .drop_duplicates("adsh", keep="last")[["adsh", "value", "tag", "ddate"]]
        .rename(
            columns={
                "value": "prior_assets",
                "tag": "tag_prior_assets",
                "ddate": "prior_assets_date",
            }
        )
    )
    prior_revenue = merged[
        merged["concept"].eq("revenue")
        & merged["qtrs"].eq(4)
        & merged["ddate"].lt(merged["period"])
        & merged["ddate"].ge(merged["period"] - pd.Timedelta(days=450))
    ].copy()
    prior_revenue = (
        prior_revenue.sort_values(["adsh", "ddate", "priority"], ascending=[True, False, True])
        .drop_duplicates("adsh", keep="first")[["adsh", "value", "tag", "ddate"]]
        .rename(
            columns={
                "value": "prior_revenue",
                "tag": "tag_prior_revenue",
                "ddate": "prior_revenue_date",
            }
        )
    )
    selected = pd.concat([flow, current_instant], ignore_index=True)
    selected = selected.sort_values(["adsh", "concept", "priority"]).drop_duplicates(
        ["adsh", "concept"], keep="first"
    )
    values = selected.pivot(index="adsh", columns="concept", values="value").reset_index()
    tags = (
        selected.pivot(index="adsh", columns="concept", values="tag")
        .add_prefix("tag_")
        .reset_index()
    )
    output = (
        submissions.merge(values, on="adsh", how="left", validate="one_to_one")
        .merge(tags, on="adsh", how="left", validate="one_to_one")
        .merge(prior_assets, on="adsh", how="left", validate="one_to_one")
        .merge(prior_revenue, on="adsh", how="left", validate="one_to_one")
    )
    for column in CONCEPT_TAGS:
        if column not in output:
            output[column] = np.nan
        tag_column = f"tag_{column}"
        if tag_column not in output:
            output[tag_column] = pd.NA
    output["gross_profit"] = output["gross_profit"].fillna(
        output["revenue"] - output["cost_of_revenue"]
    )
    output["liabilities"] = output["liabilities"].fillna(output["assets"] - output["equity"])
    denominator = output["revenue"].where(output["revenue"].abs() > 1e-12)
    average_assets = output[["assets", "prior_assets"]].mean(axis=1, skipna=False)
    output["gross_margin"] = output["gross_profit"].div(denominator)
    output["operating_margin"] = output["operating_income"].div(denominator)
    output["cash_flow_margin"] = output["operating_cash_flow"].div(denominator)
    output["net_margin"] = output["net_income"].div(denominator)
    output["return_on_assets"] = output["net_income"].div(
        average_assets.where(average_assets.abs() > 1e-12)
    )
    output["liabilities_to_assets"] = output["liabilities"].div(
        output["assets"].where(output["assets"].abs() > 1e-12)
    )
    output["equity_to_assets"] = output["equity"].div(
        output["assets"].where(output["assets"].abs() > 1e-12)
    )
    output["cash_flow_to_assets"] = output["operating_cash_flow"].div(
        average_assets.where(average_assets.abs() > 1e-12)
    )
    output["asset_growth"] = (
        output["assets"]
        .div(output["prior_assets"].where(output["prior_assets"].abs() > 1e-12))
        .sub(1.0)
    )
    output["revenue_growth"] = (
        output["revenue"]
        .div(output["prior_revenue"].where(output["prior_revenue"].abs() > 1e-12))
        .sub(1.0)
    )
    return output.sort_values(["cik", "filed", "adsh"]).reset_index(drop=True)


def parse_fsds_archive(archive_path: Path, ciks: Iterable[int]) -> pd.DataFrame:
    submissions = read_submissions(archive_path, ciks)
    numbers = read_relevant_numbers(archive_path, submissions)
    return normalize_annual_filings(submissions, numbers)


def select_sector_pilot(components: pd.DataFrame, count: int = 30) -> pd.DataFrame:
    """Deterministic round-robin sector sample that does not use model outcomes."""
    frame = components.sort_values(["sector", "ticker"]).copy()
    frame["sector_order"] = frame.groupby("sector").cumcount()
    return (
        frame.sort_values(["sector_order", "sector", "ticker"])
        .head(int(count))
        .drop(columns="sector_order")
        .reset_index(drop=True)
    )


def feature_coverage(frame: pd.DataFrame, features: list[str]) -> dict[str, Any]:
    return {
        "filings": len(frame),
        "issuers_with_filings": int(frame["cik"].nunique()) if not frame.empty else 0,
        "feature_coverage": {
            feature: float(frame[feature].notna().mean()) if len(frame) else 0.0
            for feature in features
        },
        "all_features_coverage": (
            float(frame[features].notna().all(axis=1).mean()) if len(frame) else 0.0
        ),
    }
