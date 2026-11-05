from __future__ import annotations

import json
import tomllib
from pathlib import Path

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.integrity_panel import load_integrity_corrected_sp500
from risk_managed_momentum.data.outcome_prices import audit_episode_censoring
from risk_managed_momentum.data.panel import coverage_summary
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def main() -> None:
    base = load_config(PROJECT_ROOT / "configs/research.toml")
    with (PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml").open("rb") as handle:
        hazard = tomllib.load(handle)
    with (PROJECT_ROOT / "configs/research_v1_2_integrity_expansion.toml").open("rb") as handle:
        config = tomllib.load(handle)
    price, volume, membership, resolution = load_integrity_corrected_sp500(
        PROJECT_ROOT, base, config
    )
    episodes = build_exuberance_episode_dataset(
        price,
        volume,
        base,
        hazard,
        membership=membership,
        include_unlabeled=True,
    )
    censoring = audit_episode_censoring(
        price,
        resolution.prices,
        episodes.frame,
        horizon_days=int(config["outcomes"]["horizon_days"]),
    )
    coverage = coverage_summary(price, membership)
    mature = censoring[censoring["globally_mature"]]
    unresolved = mature[mature["resolved_missing_days"].gt(0)]
    summary = {
        "specification_version": config["project"]["specification_version"],
        "panel_start": str(price.index.min().date()),
        "panel_end": str(price.index.max().date()),
        "panel_symbols": len(price.columns),
        "membership_rows": int(membership.sum().sum()),
        "median_in_membership_coverage": float(coverage["coverage_rate"].median()),
        "mean_in_membership_coverage": float(coverage["coverage_rate"].mean()),
        "symbols_below_95_percent_coverage": int(coverage["coverage_rate"].lt(0.95).sum()),
        "episode_onsets": len(episodes.frame),
        "mature_episode_onsets": len(mature),
        "repaired_mature_episode_paths": int(mature["censoring_status"].eq("resolved").sum()),
        "unresolved_mature_episode_paths": len(unresolved),
        "recent_unmatured_episode_paths": int(
            censoring["censoring_status"].eq("recent_unmatured").sum()
        ),
        "terminal_action_resolutions": int(
            resolution.audit["resolution_status"].ne("unresolved").sum()
        ),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(TABLES / "v12_membership_coverage.csv", index=False)
    censoring.to_csv(TABLES / "v12_censoring_audit.csv", index=False)
    resolution.audit.to_csv(TABLES / "v12_terminal_action_audit.csv", index=False)
    (TABLES / "v12_data_integrity_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
