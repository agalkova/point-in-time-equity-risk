from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.data.panel import build_point_in_time_panel


def _toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_sp500_panel(
    project_root: Path,
    base_config: dict,
    *,
    membership_path: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = base_config["modern_source"]
    bars = pd.read_csv(project_root / source["bars_path"])
    prehistory_path = project_root / source.get("prehistory_bars_path", "")
    if source.get("prehistory_bars_path") and prehistory_path.exists():
        prehistory = pd.read_csv(prehistory_path)
        bars = pd.concat([prehistory[bars.columns], bars], ignore_index=True)
    alias_bars = pd.read_csv(project_root / source["historical_alias_bars_path"])
    bars = pd.concat([bars, alias_bars[bars.columns]], ignore_index=True)
    membership = pd.read_csv(project_root / (membership_path or source["membership_path"]))
    aliases = _toml(project_root / source["aliases_path"])["alias"]
    return build_point_in_time_panel(bars, membership, aliases)


def load_ndx_panel(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = _toml(project_root / "configs/research_v0_7_ndx.toml")
    bars = pd.read_csv(project_root / config["data"]["bars_path"])
    membership = pd.read_csv(project_root / config["data"]["membership_path"])
    aliases = _toml(project_root / "data/reference/ndx_symbol_aliases.toml")["alias"]
    return build_point_in_time_panel(bars, membership, aliases)


def load_sp400_panel(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = _toml(project_root / "configs/research_v0_8_sp400.toml")
    bars = pd.read_csv(project_root / config["data"]["bars_path"])
    gap_path = project_root / config["data"]["historical_gap_bars_path"]
    if gap_path.exists():
        gap_bars = pd.read_csv(gap_path)
        bars = pd.concat([bars, gap_bars[bars.columns]], ignore_index=True)
    membership = pd.read_csv(project_root / config["data"]["membership_path"])
    aliases = _toml(project_root / "data/reference/sp400_symbol_aliases.toml")["alias"]
    return build_point_in_time_panel(bars, membership, aliases)
