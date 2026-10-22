from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from risk_managed_momentum.data.factors import FACTOR_URLS, download_french_factors

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output_dir = PROJECT_ROOT / "data" / "raw" / "fama_french"
    output_dir.mkdir(parents=True, exist_ok=True)
    factors = download_french_factors()
    factors.to_csv(output_dir / "daily_six_factors.csv.gz", index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "sources": FACTOR_URLS,
        "first_date": str(factors["date"].min().date()),
        "last_date": str(factors["date"].max().date()),
        "rows": len(factors),
        "units": "decimal daily returns",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
