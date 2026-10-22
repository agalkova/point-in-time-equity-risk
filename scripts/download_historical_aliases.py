from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.data.alpaca import AlpacaHistoricalClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config_path = PROJECT_ROOT / "data" / "reference" / "modern_symbol_aliases.toml"
    with config_path.open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    downloads = [row for row in aliases if row.get("download_asof")]

    load_dotenv(PROJECT_ROOT / ".env")
    client = AlpacaHistoricalClient.from_environment()
    frames: list[pd.DataFrame] = []
    records: list[dict[str, object]] = []
    for row in downloads:
        frame, manifest = client.download_daily_bars(
            [row["provider_ticker"]],
            start=row["start"],
            end=row["end"],
            feed="sip",
            adjustment="all",
            asof=row["download_asof"],
        )
        frame["alias_membership_ticker"] = row["membership_ticker"]
        frames.append(frame)
        records.append(
            {
                "membership_ticker": row["membership_ticker"],
                "provider_ticker": row["provider_ticker"],
                "asof": row["download_asof"],
                "rows": manifest.rows,
                "missing": manifest.missing_symbols,
            }
        )

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    output_dir = PROJECT_ROOT / "data" / "raw" / "alpaca"
    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_dir / "bars_historical_aliases_all.csv.gz", index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "adjustment": "all",
        "feed": "sip",
        "downloads": records,
        "rows": int(len(combined)),
    }
    (output_dir / "bars_historical_aliases_all.manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
