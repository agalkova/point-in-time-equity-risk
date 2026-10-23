from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.data.alpaca import AlpacaHistoricalClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_8_sp400.toml").open("rb") as handle:
        config = tomllib.load(handle)
    membership_path = PROJECT_ROOT / config["data"]["membership_path"]
    if not membership_path.exists():
        raise SystemExit("Missing S&P 400 membership. Run scripts/build_sp400_membership.py first.")
    membership = pd.read_csv(membership_path)
    symbols = sorted(membership["ticker"].dropna().astype(str).unique())
    load_dotenv(PROJECT_ROOT / ".env")
    client = AlpacaHistoricalClient.from_environment()
    frame, manifest = client.download_daily_bars_batched(
        symbols,
        start=config["universe"]["membership_start"],
        end=config["universe"]["evaluation_end"],
        adjustment="all",
        feed="sip",
        batch_size=100,
    )
    output_path = PROJECT_ROOT / config["data"]["bars_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, compression="gzip")
    output_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2) + "\n"
    )
    print(f"Saved {len(frame):,} adjusted SIP bars for {len(symbols)} requested tickers")
    print(f"Missing symbols: {manifest.missing_symbols}")


if __name__ == "__main__":
    main()
