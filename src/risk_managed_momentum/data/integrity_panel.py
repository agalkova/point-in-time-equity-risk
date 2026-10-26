from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from risk_managed_momentum.data.corporate_actions import load_corporate_action_overrides
from risk_managed_momentum.data.outcome_prices import OutcomePriceResolution, resolve_outcome_prices
from risk_managed_momentum.data.universes import load_sp500_panel


def load_integrity_corrected_sp500(
    project_root: Path,
    base_config: dict[str, Any],
    integrity_config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, OutcomePriceResolution]:
    """Load the frozen expanded panel and a separate outcome-valuation panel."""
    data = integrity_config["data"]
    price, volume, membership = load_sp500_panel(
        project_root,
        base_config,
        membership_path=data["membership_path"],
    )
    provider_actions = pd.read_csv(project_root / data["corporate_actions_path"], low_memory=False)
    overrides = load_corporate_action_overrides(
        project_root / data["corporate_action_overrides_path"]
    )
    actions = pd.concat([provider_actions, overrides], ignore_index=True, sort=False)
    successor_bars = pd.read_csv(project_root / data["successor_bars_path"])
    successor_bars["date"] = pd.to_datetime(successor_bars["date"]).dt.normalize()
    successor = successor_bars.pivot(index="date", columns="ticker", values="close").reindex(
        price.index
    )
    successor = successor.combine_first(price)
    resolution = resolve_outcome_prices(
        price,
        actions,
        successor_prices=successor,
        maximum_internal_gap_days=int(integrity_config["outcomes"]["maximum_internal_gap_days"]),
        action_match_calendar_days=int(integrity_config["outcomes"]["action_match_calendar_days"]),
    )
    return price, volume, membership, resolution
