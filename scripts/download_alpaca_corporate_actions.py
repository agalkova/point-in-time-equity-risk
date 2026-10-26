from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from risk_managed_momentum.data.corporate_actions import AlpacaCorporateActionsClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Alpaca corporate-action history")
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser.parse_args()


def read_symbols(path: Path) -> list[str]:
    if path.suffix.lower() in {".txt", ".list"}:
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    table = pd.read_csv(path)
    if "ticker" not in table:
        raise ValueError("Symbols file must contain a ticker column")
    return table["ticker"].dropna().astype(str).tolist()


def main() -> None:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    client = AlpacaCorporateActionsClient.from_environment()
    frame, manifest = client.download(
        read_symbols(args.symbols_file),
        start=args.start,
        end=args.end,
        batch_size=args.batch_size,
    )
    output_dir = PROJECT_ROOT / "data/raw/alpaca"
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"corporate_actions_{args.start}_{args.end}"
    frame.to_csv(output_dir / f"{stem}.csv.gz", index=False, compression="gzip")
    (output_dir / f"{stem}.manifest.json").write_text(
        json.dumps(manifest.to_dict(), indent=2) + "\n"
    )
    print(json.dumps({"rows": len(frame), "types": manifest.action_types}, indent=2))


if __name__ == "__main__":
    main()
