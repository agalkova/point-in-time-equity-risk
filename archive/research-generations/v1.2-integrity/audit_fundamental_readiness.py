from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.integrity_panel import load_integrity_corrected_sp500
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.features.fundamentals import (
    build_filing_features,
    point_in_time_fundamentals,
)

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
        outcome_price=resolution.prices,
    ).frame
    annual = pd.read_csv(
        PROJECT_ROOT / "data/interim/sec/annual_companyfacts.csv.gz",
        parse_dates=["end", "filed"],
    )
    filing = build_filing_features(annual)
    joined = point_in_time_fundamentals(filing, episodes[["date", "ticker"]])
    supported = {
        "gross_margin": "fundamental_gross_margin",
        "operating_margin": "fundamental_operating_margin",
        "cash_flow_margin": None,
    }
    # The downloaded duration facts support cash-flow margin directly.
    cash_flow_margin = annual[
        ["ticker", "fiscal_year", "filed", "operating_cash_flow", "revenue"]
    ].copy()
    cash_flow_margin["cash_flow_margin"] = cash_flow_margin["operating_cash_flow"].div(
        cash_flow_margin["revenue"].where(cash_flow_margin["revenue"].abs() > 1e-12)
    )
    cash_join = point_in_time_fundamentals(
        cash_flow_margin.rename(columns={"cash_flow_margin": "fundamental_gross_margin"}),
        episodes[["date", "ticker"]],
    )
    joined["cash_flow_margin"] = cash_join["fundamental_gross_margin"]
    joined["gross_margin"] = joined[supported["gross_margin"]]
    joined["operating_margin"] = joined[supported["operating_margin"]]

    requested = list(config["fundamentals"]["features"])
    available = ["gross_margin", "operating_margin", "cash_flow_margin"]
    unavailable = [feature for feature in requested if feature not in available]
    fully_covered = joined[available].notna().all(axis=1)
    issuer_coverage = annual["ticker"].nunique() / len(price.columns)
    gate_passed = not unavailable and issuer_coverage >= 0.5
    summary = {
        "requested_features": requested,
        "available_features": available,
        "unavailable_features": unavailable,
        "fundamental_issuers": int(annual["ticker"].nunique()),
        "historical_panel_symbols": len(price.columns),
        "issuer_coverage_rate": issuer_coverage,
        "episodes": len(episodes),
        "episodes_with_all_available_features": int(fully_covered.sum()),
        "episode_coverage_rate": float(fully_covered.mean()),
        "official_sec_access_status": "blocked_by_upstream_http_403",
        "current_data_limitation": "22-ticker current-survivor pilot from a third-party normalizer",
        "minimum_issuer_coverage_gate": 0.5,
        "ablation_gate_passed": gate_passed,
        "decision": (
            "run_point_in_time_ablation" if gate_passed else "do_not_fit_biased_fundamental_model"
        ),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / "v12_fundamental_readiness.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
