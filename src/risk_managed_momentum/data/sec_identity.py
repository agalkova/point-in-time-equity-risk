from __future__ import annotations

import json
import re
import zipfile
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

LEGAL_WORDS = {
    "co",
    "company",
    "corp",
    "corporation",
    "de",
    "inc",
    "incorporated",
    "limited",
    "ltd",
    "ma",
    "mn",
    "new",
    "nv",
    "oh",
    "plc",
}


def normalize_sec_ticker(value: object) -> str:
    return str(value).strip().upper().replace(".", "-")


def normalize_company_name(value: object) -> str:
    if pd.isna(value):
        return ""
    words = re.sub(r"[^A-Z0-9]+", " ", str(value).upper().replace("&", " AND ")).split()
    cleaned = [word.lower() for word in words if word.lower() not in LEGAL_WORDS]
    if cleaned and cleaned[0] == "the":
        cleaned = cleaned[1:]
    return " ".join(cleaned)


def name_similarity(left: object, right: object) -> float:
    a = normalize_company_name(left)
    b = normalize_company_name(right)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def company_name_anchor(value: object) -> str:
    words = normalize_company_name(value).split()
    if not words:
        return ""
    return " ".join(words[:2]) if len(words[0]) <= 3 and len(words) > 1 else words[0]


def load_sec_ticker_registry(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text())
    rows = list(payload.values()) if isinstance(payload, dict) else payload
    frame = pd.DataFrame(rows).rename(columns={"cik_str": "cik", "title": "sec_name"})
    frame["cik"] = pd.to_numeric(frame["cik"], errors="raise").astype("int64")
    frame["sec_ticker"] = frame["ticker"].map(normalize_sec_ticker)
    return frame[["sec_ticker", "cik", "sec_name"]].drop_duplicates()


def load_fsds_submission_registry(archive_path: Path) -> pd.DataFrame:
    """Load issuer names and CIKs from an official SEC FSDS quarterly archive."""
    with zipfile.ZipFile(archive_path) as archive:
        submission_files = [name for name in archive.namelist() if name.lower().endswith("sub.txt")]
        if len(submission_files) != 1:
            raise ValueError(
                f"Expected one sub.txt in {archive_path}, found {len(submission_files)}"
            )
        with archive.open(submission_files[0]) as handle:
            frame = pd.read_csv(handle, sep="\t", usecols=["cik", "name", "filed"])
    frame["cik"] = pd.to_numeric(frame["cik"], errors="coerce").astype("Int64")
    frame = frame.dropna(subset=["cik", "name"]).rename(columns={"name": "sec_name"})
    frame["normalized_name"] = frame["sec_name"].map(normalize_company_name)
    filed = pd.to_numeric(frame["filed"], errors="coerce").astype("Int64").astype("string")
    frame["filed"] = pd.to_datetime(filed, format="%Y%m%d", errors="coerce")
    return frame[["cik", "sec_name", "normalized_name", "filed"]].drop_duplicates()


def membership_intervals(daily: pd.DataFrame, *, gap_days: int = 7) -> pd.DataFrame:
    frame = daily[["date", "ticker"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["ticker"] = frame["ticker"].map(normalize_sec_ticker)
    rows: list[dict[str, object]] = []
    for ticker, group in frame.sort_values("date").groupby("ticker", sort=True):
        dates = group["date"].drop_duplicates().sort_values()
        segment = dates.diff().dt.days.fillna(0).gt(gap_days).cumsum()
        for interval_number, (_, interval_dates) in enumerate(dates.groupby(segment), start=1):
            rows.append(
                {
                    "ticker": ticker,
                    "interval": interval_number,
                    "valid_from": interval_dates.min(),
                    "valid_to": interval_dates.max(),
                    "membership_days": len(interval_dates),
                }
            )
    return pd.DataFrame(rows)


def _nearby_name(
    changes: pd.DataFrame,
    ticker: str,
    date: pd.Timestamp,
    ticker_column: str,
    name_column: str,
) -> str | None:
    candidates = changes[changes[ticker_column].map(normalize_sec_ticker).eq(ticker)].copy()
    if candidates.empty:
        return None
    candidates["distance"] = (candidates["date"] - date).abs().dt.days
    candidate = candidates.sort_values(["distance", "date"]).iloc[0]
    if candidate["distance"] > 14 or pd.isna(candidate[name_column]):
        return None
    return str(candidate[name_column])


def attach_interval_names(
    intervals: pd.DataFrame,
    current: pd.DataFrame,
    changes: pd.DataFrame,
) -> pd.DataFrame:
    result = intervals.copy()
    changes = changes.copy()
    changes["date"] = pd.to_datetime(changes["date"], errors="raise").dt.normalize()
    current_names = (
        current.assign(normalized_ticker=current["ticker"].map(normalize_sec_ticker))
        .set_index("normalized_ticker")["security"]
        .to_dict()
    )
    latest = result["valid_to"].max()
    names = []
    sources = []
    for row in result.itertuples(index=False):
        added = _nearby_name(changes, row.ticker, row.valid_from, "added_ticker", "added_security")
        removed = _nearby_name(
            changes, row.ticker, row.valid_to, "removed_ticker", "removed_security"
        )
        if row.valid_to == latest and row.ticker in current_names:
            name, source = current_names[row.ticker], "current_components"
        elif removed:
            name, source = removed, "membership_removal"
        elif added:
            name, source = added, "membership_addition"
        elif row.ticker in current_names:
            name, source = current_names[row.ticker], "current_name_fallback"
        else:
            name, source = None, "missing"
        names.append(name)
        sources.append(source)
    result["membership_name"] = names
    result["name_source"] = sources
    return result


def build_sec_identity_map(
    intervals: pd.DataFrame,
    current: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    minimum_name_similarity: float = 0.72,
) -> pd.DataFrame:
    current_map = current.assign(
        normalized_ticker=current["ticker"].map(normalize_sec_ticker)
    ).set_index("normalized_ticker")
    registry_groups = {ticker: group for ticker, group in registry.groupby("sec_ticker")}
    latest = intervals["valid_to"].max()
    multiple_intervals = intervals.groupby("ticker").size().gt(1).to_dict()
    rows = []
    for row in intervals.itertuples(index=False):
        cik = pd.NA
        sec_name = pd.NA
        source = "unresolved"
        confidence = "none"
        similarity = 0.0
        status = "REVIEW"
        reason = "No safe SEC ticker/CIK match"
        current_row = current_map.loc[row.ticker] if row.ticker in current_map.index else None
        if current_row is not None and row.valid_to == latest:
            cik = int(current_row["cik"])
            sec_name = current_row["security"]
            source = "sp500_current_components"
            confidence = "verified"
            similarity = name_similarity(row.membership_name, sec_name)
            status = "RESOLVED"
            reason = "Current S&P constituent CIK"
        else:
            candidates = registry_groups.get(row.ticker)
            if candidates is not None and len(candidates) == 1:
                candidate = candidates.iloc[0]
                similarity = name_similarity(row.membership_name, candidate["sec_name"])
                reused = bool(multiple_intervals.get(row.ticker, False))
                if row.membership_name and similarity >= minimum_name_similarity and not reused:
                    cik = int(candidate["cik"])
                    sec_name = candidate["sec_name"]
                    source = "sec_company_tickers"
                    confidence = "high"
                    status = "RESOLVED"
                    reason = "Unique ticker and membership-name agreement"
                elif reused:
                    reason = "Ticker has multiple membership intervals; historical identity review required"
                else:
                    reason = "SEC ticker exists but company name does not clear threshold"
            elif candidates is not None:
                reason = "SEC ticker maps to multiple CIKs"
        rows.append(
            {
                **row._asdict(),
                "cik": cik,
                "sec_name": sec_name,
                "identity_source": source,
                "confidence": confidence,
                "name_similarity": similarity,
                "status": status,
                "reason": reason,
            }
        )
    result = pd.DataFrame(rows)
    result["cik"] = result["cik"].astype("Int64")
    return result


def resolve_identity_names(
    identities: pd.DataFrame,
    entities: pd.DataFrame,
    *,
    minimum_similarity: float = 0.92,
    minimum_margin: float = 0.05,
) -> pd.DataFrame:
    """Resolve review rows only when an SEC filing name has one decisive CIK match."""
    result = identities.copy()
    candidates = entities.dropna(subset=["cik", "normalized_name"]).copy()
    candidates = candidates[candidates["normalized_name"].ne("")]
    for index, row in result[result["status"].ne("RESOLVED")].iterrows():
        target = normalize_company_name(row["membership_name"])
        if not target:
            continue
        eligible = candidates
        if (
            "filed" in eligible
            and pd.notna(row.get("valid_from"))
            and pd.notna(row.get("valid_to"))
        ):
            lower = pd.Timestamp(row["valid_from"]) - pd.Timedelta(days=450)
            upper = pd.Timestamp(row["valid_to"]) + pd.Timedelta(days=450)
            eligible = eligible[eligible["filed"].between(lower, upper, inclusive="both")]
        candidate_rows = list(eligible.itertuples(index=False))
        best_by_cik: dict[int, tuple[float, int, object]] = {}
        for position, candidate in enumerate(candidate_rows):
            if company_name_anchor(target) != company_name_anchor(candidate.normalized_name):
                continue
            score = SequenceMatcher(None, target, candidate.normalized_name).ratio()
            cik = int(candidate.cik)
            if cik not in best_by_cik or score > best_by_cik[cik][0]:
                best_by_cik[cik] = (score, position, candidate)
        scored = sorted(
            best_by_cik.values(),
            key=lambda item: item[0],
            reverse=True,
        )
        if not scored:
            continue
        best_score, _, best = scored[0]
        runner_up_score = scored[1][0] if len(scored) > 1 else 0.0
        margin = best_score - runner_up_score
        if best_score < minimum_similarity or margin < minimum_margin:
            continue
        result.at[index, "cik"] = int(best.cik)
        result.at[index, "sec_name"] = best.sec_name
        result.at[index, "identity_source"] = "sec_fsds_submission_name"
        result.at[index, "confidence"] = "high"
        result.at[index, "name_similarity"] = best_score
        result.at[index, "status"] = "RESOLVED"
        result.at[index, "reason"] = (
            f"Unique high-similarity SEC filing-name match (runner-up margin {margin:.3f})"
        )

    result["cik"] = result["cik"].astype("Int64")
    return result


def carry_forward_resolved_identities(
    identities: pd.DataFrame,
    previous: pd.DataFrame,
) -> pd.DataFrame:
    """Preserve reviewed interval resolutions when their source archives are no longer present."""
    keys = ["ticker", "interval", "valid_from", "valid_to"]
    fields = [
        "cik",
        "sec_name",
        "identity_source",
        "confidence",
        "name_similarity",
        "status",
        "reason",
    ]
    current = identities.copy()
    prior = previous.copy()
    for column in ["valid_from", "valid_to"]:
        current[column] = pd.to_datetime(current[column], errors="raise").dt.normalize()
        prior[column] = pd.to_datetime(prior[column], errors="raise").dt.normalize()
    prior = prior[prior["status"].eq("RESOLVED")][keys + fields].drop_duplicates(keys)
    merged = current.merge(prior, on=keys, how="left", suffixes=("", "_prior"))
    carry = merged["status"].ne("RESOLVED") & merged["status_prior"].eq("RESOLVED")
    for field in fields:
        merged.loc[carry, field] = merged.loc[carry, f"{field}_prior"]
    merged = merged.drop(columns=[f"{field}_prior" for field in fields])
    merged["cik"] = merged["cik"].astype("Int64")
    return merged
