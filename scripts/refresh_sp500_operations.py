from __future__ import annotations

import argparse
import json
import os
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.alpaca import AlpacaHistoricalClient
from risk_managed_momentum.data.membership import (
    WIKIPEDIA_SP500_HISTORY_URL,
    WIKIPEDIA_SP500_URL,
    daily_membership,
    fetch_wikipedia_membership,
    symbols_needed_for_period,
)
from risk_managed_momentum.operations.monitoring import file_sha256
from risk_managed_momentum.operations.refresh import (
    atomic_write_dataframes,
    merge_bar_history,
    strict_json_bytes,
    validate_operational_panel,
)
from risk_managed_momentum.operations.runtime import exclusive_run_lock

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely refresh operational S&P 500 inputs")
    parser.add_argument("--end", help="Requested end date; defaults to today")
    parser.add_argument("--overlap-calendar-days", type=int, default=400)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser.parse_args()


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def main() -> None:
    args = parse_args()
    if args.overlap_calendar_days < 180:
        raise ValueError("Refresh overlap must be at least 180 calendar days")
    requested_end = (
        pd.Timestamp(args.end).normalize() if args.end else pd.Timestamp.today().normalize()
    )
    query_end = requested_end if args.end else requested_end - pd.Timedelta(days=1)
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    operations = load_toml(PROJECT_ROOT / "configs/operations.toml")
    source_config = base_config["modern_source"]
    bars_path = PROJECT_ROOT / source_config["bars_path"]
    alias_bars_path = PROJECT_ROOT / source_config["historical_alias_bars_path"]
    membership_path = PROJECT_ROOT / source_config["membership_path"]
    aliases = load_toml(PROJECT_ROOT / source_config["aliases_path"])["alias"]
    lock_path = PROJECT_ROOT / "reports/operations/.locks/sp500-refresh.lock"

    load_dotenv(PROJECT_ROOT / ".env")
    with exclusive_run_lock(lock_path):
        existing = pd.read_csv(bars_path)
        existing["date"] = pd.to_datetime(existing["date"], errors="raise").dt.normalize()
        existing_last = pd.Timestamp(existing["date"].max()).normalize()
        replace_from = max(
            pd.Timestamp("2019-06-01"),
            existing_last - pd.Timedelta(days=args.overlap_calendar_days),
        )

        membership_source = fetch_wikipedia_membership()
        membership = daily_membership(
            membership_source,
            start="2019-06-01",
            end=requested_end,
        )
        all_historical_symbols = symbols_needed_for_period(
            membership_source,
            start="2019-06-01",
        )
        recent_changes = membership_source.changes[
            membership_source.changes["date"].ge(replace_from)
        ]
        symbols = set(membership_source.current["ticker"].dropna().astype(str))
        symbols.update(recent_changes["added_ticker"].dropna().astype(str))
        symbols.update(recent_changes["removed_ticker"].dropna().astype(str))
        for alias in aliases:
            if pd.Timestamp(alias["end"]) >= replace_from:
                symbols.add(str(alias["provider_ticker"]))

        client = AlpacaHistoricalClient.from_environment()
        incoming, download_manifest = client.download_daily_bars_batched(
            sorted(symbols),
            start=str(replace_from.date()),
            # The free delayed-SIP entitlement rejects a date boundary containing today.
            # An ordinary run requests through yesterday; weekend handling naturally returns
            # the latest completed trading day. Explicit historical replays keep their cutoff.
            end=str(query_end.date()),
            adjustment="all",
            feed="sip",
            batch_size=args.batch_size,
        )
        if incoming.empty:
            raise RuntimeError("Alpaca refresh returned no bars")
        merged = merge_bar_history(existing, incoming, replace_from=replace_from)
        alias_bars = pd.read_csv(alias_bars_path)
        validation = validate_operational_panel(
            merged,
            alias_bars,
            membership,
            aliases,
            minimum_latest_coverage=float(
                operations["quality_gates"]["minimum_latest_membership_coverage"]
            ),
        )
        market_date = pd.Timestamp(validation["market_data_date"])
        staleness = int((requested_end - market_date).days)
        maximum_staleness = int(
            operations["quality_gates"]["maximum_market_data_staleness_calendar_days"]
        )
        if staleness > maximum_staleness:
            raise RuntimeError(
                f"Refreshed market data remains {staleness} days stale; maximum is "
                f"{maximum_staleness}"
            )

        membership_dir = membership_path.parent
        atomic_write_dataframes(
            {
                bars_path: merged,
                membership_path: membership,
                membership_dir / "sp500_current_components.csv": membership_source.current,
                membership_dir / "sp500_changes.csv": membership_source.changes,
            },
            csv_options={
                bars_path: {"compression": "gzip"},
                membership_path: {"compression": "gzip"},
            },
        )
        symbols_path = membership_dir / "sp500_symbols.txt"
        symbols_path.write_text("\n".join(all_historical_symbols) + "\n")
        membership_manifest = {
            "source_urls": [WIKIPEDIA_SP500_URL, WIKIPEDIA_SP500_HISTORY_URL],
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "start": "2019-06-01",
            "end": str(requested_end.date()),
            "current_constituents": int(membership_source.current["ticker"].nunique()),
            "change_rows": len(membership_source.changes),
            "requested_symbols": len(symbols),
            "historical_symbols": len(all_historical_symbols),
            "membership_rows": len(membership),
        }
        (membership_dir / "manifest.json").write_bytes(strict_json_bytes(membership_manifest))
        receipt = {
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "requested_end": str(requested_end.date()),
            "replace_from": str(replace_from.date()),
            "previous_market_data_date": str(existing_last.date()),
            **validation,
            "download": download_manifest.to_dict(),
            "bars_sha256": file_sha256(bars_path),
            "membership_sha256": file_sha256(membership_path),
        }
        receipt_root = PROJECT_ROOT / "reports/operations/data_refresh"
        receipt_root.mkdir(parents=True, exist_ok=True)
        receipt_path = receipt_root / f"sp500_{market_date.date()}.json"
        with tempfile.NamedTemporaryFile(dir=receipt_root, delete=False) as handle:
            handle.write(strict_json_bytes(receipt))
            temporary_receipt = Path(handle.name)
        os.replace(temporary_receipt, receipt_path)
        print(json.dumps({**validation, "receipt": str(receipt_path)}, indent=2))


if __name__ == "__main__":
    main()
