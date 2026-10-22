from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.sec import (
    download_companyfacts_batch,
    normalize_companyfacts_files,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def pilot_companies(components: pd.DataFrame) -> pd.DataFrame:
    """Select two established, unique issuers per sector without outcome information."""
    frame = components.copy()
    frame["Date added"] = pd.to_datetime(frame["Date added"], errors="coerce")
    frame = frame[frame["Date added"].le(pd.Timestamp("2018-12-31"))]
    frame = frame.sort_values(["sector", "ticker"]).drop_duplicates(["sector", "cik"])
    return frame.groupby("sector", group_keys=False).head(2)[
        ["ticker", "security", "sector", "cik", "Date added"]
    ].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a small SEC fundamentals pilot")
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("SEC_USER_AGENT"),
        help="SEC-compliant identity such as 'Name email@example.com' (or SEC_USER_AGENT)",
    )
    args = parser.parse_args()
    if not args.user_agent:
        raise SystemExit("Set SEC_USER_AGENT to an identifying name and email address")

    components_path = PROJECT_ROOT / "data/interim/membership/sp500_current_components.csv"
    companies = pilot_companies(pd.read_csv(components_path))
    raw_directory = PROJECT_ROOT / "data/raw/sec/companyfacts"
    results = download_companyfacts_batch(
        companies,
        raw_directory,
        user_agent=args.user_agent,
    )
    normalized = normalize_companyfacts_files([result.path for result in results])
    output_path = PROJECT_ROOT / "data/interim/sec/annual_companyfacts.csv.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output_path, index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "source": "https://data.sec.gov/api/xbrl/companyfacts/",
        "selection_rule": (
            "first two unique-CIK tickers alphabetically within each current GICS sector, "
            "restricted to S&P 500 additions on or before 2018-12-31"
        ),
        "companies": [
            {
                "ticker": result.ticker,
                "cik": result.cik,
                "entity_name": result.entity_name,
            }
            for result in results
        ],
        "normalized_rows": len(normalized),
    }
    (output_path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Downloaded {len(results)} issuers and normalized {len(normalized)} annual filings")
    print(output_path)


if __name__ == "__main__":
    main()
