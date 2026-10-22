from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from download_sec_fundamentals import pilot_companies

from risk_managed_momentum.data.ptdata import (
    PTDATA_METRICS,
    download_ptdata_history,
    normalize_ptdata_files,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    components = pd.read_csv(
        PROJECT_ROOT / "data/interim/membership/sp500_current_components.csv"
    )
    companies = pilot_companies(components)
    paths = download_ptdata_history(
        companies["ticker"].tolist(),
        PROJECT_ROOT / "data/raw/ptdata/fundamentals",
    )
    normalized = normalize_ptdata_files(paths)
    output_path = PROJECT_ROOT / "data/interim/sec/annual_companyfacts.csv.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output_path, index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "provider": "ptdata",
        "upstream_source_reported_by_provider": "SEC EDGAR XBRL Companyfacts",
        "endpoint": "https://api.ptdata.io/v1/fundamentals",
        "methodology": "https://github.com/ptdata-io/ptdata-methodology",
        "fiscal_years": [2018, 2025],
        "metrics": list(PTDATA_METRICS),
        "raw_responses": len(paths),
        "normalized_rows": len(normalized),
        "limitations": [
            "Third-party normalization layer; not a direct SEC download.",
            "Latest version retrieved as of the query date is attached to its returned knowledge date.",
            "Balance-sheet instant concepts were unavailable, so the pilot uses duration metrics.",
        ],
    }
    (output_path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Downloaded {len(paths)} point-in-time responses and normalized {len(normalized)} rows")
    print(output_path)


if __name__ == "__main__":
    main()
