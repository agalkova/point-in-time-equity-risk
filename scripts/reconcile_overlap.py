from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.data.reconcile import reconcile_legacy_overlap


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare legacy and Alpaca overlap data")
    parser.add_argument("--raw-bars", required=True, type=Path)
    parser.add_argument("--adjusted-bars", required=True, type=Path)
    parser.add_argument(
        "--mapping",
        type=Path,
        default=PROJECT_ROOT / "data" / "reference" / "pilot_mapping.toml",
    )
    return parser.parse_args()


def read_mapping(path: Path) -> dict[str, str]:
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    return {
        row["provider_ticker"].upper(): row["legacy_ticker"].upper()
        for row in payload["security"]
    }


def main() -> None:
    args = parse_args()
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    price, volume = load_legacy_wide(
        config["legacy_source"]["price_path"],
        config["legacy_source"]["volume_path"],
    )
    raw_bars = pd.read_csv(args.raw_bars)
    adjusted_bars = pd.read_csv(args.adjusted_bars)
    detail, summary = reconcile_legacy_overlap(
        price,
        volume,
        raw_bars,
        adjusted_bars,
        read_mapping(args.mapping),
    )
    output_dir = PROJECT_ROOT / "reports" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output_dir / "pilot_overlap_detail.csv.gz", index=False, compression="gzip")
    summary.to_csv(output_dir / "pilot_overlap_summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

