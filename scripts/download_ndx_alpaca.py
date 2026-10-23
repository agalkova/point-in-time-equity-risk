from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.data.alpaca import AlpacaHistoricalClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with (PROJECT_ROOT / "configs/research_v0_7_ndx.toml").open("rb") as handle:
        config = tomllib.load(handle)
    membership_path = PROJECT_ROOT / config["data"]["membership_path"]
    if not membership_path.exists():
        raise SystemExit("Missing NDX membership. Run scripts/download_ndx_membership.py first.")
    membership = pd.read_csv(membership_path)
    symbols = sorted(membership["ticker"].dropna().astype(str).unique())
    with (PROJECT_ROOT / "data/reference/ndx_symbol_aliases.toml").open("rb") as handle:
        aliases = tomllib.load(handle)["alias"]
    symbols = sorted(set(symbols) | {row["provider_ticker"] for row in aliases})
    load_dotenv(PROJECT_ROOT / ".env")
    client = AlpacaHistoricalClient.from_environment()
    frame, manifest = client.download_daily_bars_batched(
        symbols,
        start="2019-06-01",
        end=config["universe"]["evaluation_end"],
        adjustment="all",
        feed="sip",
        batch_size=100,
    )
    output_path = PROJECT_ROOT / config["data"]["bars_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, compression="gzip")
    returned = set(frame["ticker"].unique())
    resolved_by_alias = {
        row["membership_ticker"]: row["provider_ticker"]
        for row in aliases
        if row["membership_ticker"] in manifest.missing_symbols
        and row["provider_ticker"] in returned
    }
    unresolved = sorted(set(manifest.missing_symbols) - set(resolved_by_alias))
    manifest_payload = manifest.to_dict()
    manifest_payload["missing_symbols_resolved_by_alias"] = resolved_by_alias
    manifest_payload["unresolved_missing_symbols"] = unresolved
    output_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest_payload, indent=2) + "\n"
    )
    print(f"Saved {len(frame):,} adjusted SIP bars for {len(symbols)} requested tickers")
    print(f"Directly missing but resolved by alias: {resolved_by_alias}")
    print(f"Unresolved missing symbols: {unresolved}")


if __name__ == "__main__":
    main()
