from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.data.alpaca import AlpacaHistoricalClient
from risk_managed_momentum.data.panel import build_point_in_time_panel, coverage_summary

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_8_sp400.toml").open("rb") as handle:
        config = tomllib.load(handle)
    bars = pd.read_csv(PROJECT_ROOT / config["data"]["bars_path"])
    membership = pd.read_csv(PROJECT_ROOT / config["data"]["membership_path"])
    membership["date"] = pd.to_datetime(membership["date"]).dt.normalize()
    with (PROJECT_ROOT / "data/reference/sp400_symbol_aliases.toml").open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    price, _, member = build_point_in_time_panel(bars, membership, aliases)
    coverage = coverage_summary(price, member)
    targets = coverage.loc[coverage["coverage_rate"].lt(0.95), "ticker"].tolist()

    load_dotenv(PROJECT_ROOT / ".env")
    client = AlpacaHistoricalClient.from_environment()
    frames = []
    records = []
    for ticker in targets:
        dates = membership.loc[membership["ticker"].eq(ticker), "date"]
        start = str(dates.min().date())
        end = str(dates.max().date())
        frame, manifest = client.download_daily_bars(
            [ticker],
            start=start,
            end=end,
            adjustment="all",
            feed="sip",
            asof=start,
        )
        frames.append(frame)
        records.append(
            {
                "ticker": ticker,
                "start": start,
                "end": end,
                "rows": len(frame),
                "returned_symbols": manifest.returned_symbols,
                "missing_symbols": manifest.missing_symbols,
            }
        )

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=bars.columns)
    output_path = PROJECT_ROOT / config["data"]["historical_gap_bars_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False, compression="gzip")
    manifest = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "selection_rule": "in-membership price coverage below 0.95 before model evaluation",
        "requested_tickers": targets,
        "rows": len(combined),
        "requests": records,
    }
    output_path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
