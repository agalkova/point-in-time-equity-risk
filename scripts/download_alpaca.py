from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.data.alpaca import AlpacaHistoricalClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download historical Alpaca SIP daily bars")
    parser.add_argument("--symbols-file", required=True, type=Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--adjustment", choices=["raw", "split", "dividend", "spin-off", "all"], default="raw")
    parser.add_argument("--asof")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--output-stem")
    return parser.parse_args()


def read_symbols(path: Path) -> list[str]:
    if path.suffix.lower() in {".txt", ".list"}:
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    table = pd.read_csv(path)
    if "ticker" not in table.columns:
        raise ValueError("Symbols file must contain a 'ticker' column")
    return table["ticker"].dropna().astype(str).tolist()


def main() -> None:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    client = AlpacaHistoricalClient.from_environment()
    frame, manifest = client.download_daily_bars_batched(
        read_symbols(args.symbols_file),
        start=args.start,
        end=args.end,
        adjustment=args.adjustment,
        feed="sip",
        asof=args.asof,
        batch_size=args.batch_size,
    )

    stem = args.output_stem or f"bars_{args.start}_{args.end}_{args.adjustment}"
    if Path(stem).name != stem:
        raise ValueError("Output stem must be a filename stem, not a path")
    output_dir = PROJECT_ROOT / "data" / "raw" / "alpaca"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / f"{stem}.csv.gz"
    manifest_path = output_dir / f"{stem}.manifest.json"
    frame.to_csv(data_path, index=False, compression="gzip")
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n")

    print(f"Saved {len(frame):,} rows to {data_path}")
    print(f"Missing symbols: {len(manifest.missing_symbols)}")


if __name__ == "__main__":
    main()

