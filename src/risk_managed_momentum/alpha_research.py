from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.panel import build_point_in_time_panel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALPHA_CONFIG_PATH = (
    PROJECT_ROOT
    / "archive"
    / "research-generations"
    / "v0.3-alpha"
    / "research_v0_3_alpha.toml"
)


def load_alpha_config(path: Path = ALPHA_CONFIG_PATH) -> dict:
    """Load the frozen v0.3 alpha specification used by later comparisons."""
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_modern_panel(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the dated market and membership panel shared by alpha studies."""
    source = config["modern_source"]
    bars = pd.read_csv(source["bars_path"])
    aliases = pd.read_csv(source["historical_alias_bars_path"])
    bars = pd.concat([bars, aliases[bars.columns]], ignore_index=True)
    membership = pd.read_csv(source["membership_path"])
    with Path(source["aliases_path"]).open("rb") as handle:
        ticker_aliases = tomllib.load(handle)["alias"]
    return build_point_in_time_panel(bars, membership, ticker_aliases)


def annual_returns(daily: pd.DataFrame) -> list[dict[str, float | int]]:
    """Compound daily net returns into calendar-year returns."""
    work = daily.copy()
    work["year"] = pd.to_datetime(work["date"]).dt.year
    return [
        {
            "year": int(year),
            "return": float((1.0 + group["net_return"]).prod() - 1.0),
        }
        for year, group in work.groupby("year")
    ]
