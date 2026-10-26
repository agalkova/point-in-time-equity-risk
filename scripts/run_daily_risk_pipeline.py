from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.universes import (
    load_ndx_panel,
    load_sp400_panel,
    load_sp500_panel,
)
from risk_managed_momentum.operations.artifacts import publish_atomic_run
from risk_managed_momentum.operations.monitoring import file_sha256
from risk_managed_momentum.operations.pipeline import score_and_monitor
from risk_managed_momentum.operations.registry import (
    canonical_json_bytes,
    feature_schema_digest,
    load_active_model,
)
from risk_managed_momentum.prospective import content_digest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def source_paths(universe: str, base_config: dict) -> list[Path]:
    if universe == "sp500":
        source = base_config["modern_source"]
        return [
            PROJECT_ROOT / source["bars_path"],
            PROJECT_ROOT / source["historical_alias_bars_path"],
            PROJECT_ROOT / source["membership_path"],
            PROJECT_ROOT / source["aliases_path"],
        ]
    if universe == "ndx":
        config = load_toml(PROJECT_ROOT / "configs/research_v0_7_ndx.toml")
        return [
            PROJECT_ROOT / config["data"]["bars_path"],
            PROJECT_ROOT / config["data"]["membership_path"],
            PROJECT_ROOT / "data/reference/ndx_symbol_aliases.toml",
        ]
    config = load_toml(PROJECT_ROOT / "configs/research_v0_8_sp400.toml")
    paths = [
        PROJECT_ROOT / config["data"]["bars_path"],
        PROJECT_ROOT / config["data"]["membership_path"],
        PROJECT_ROOT / "data/reference/sp400_symbol_aliases.toml",
    ]
    gap = PROJECT_ROOT / config["data"]["historical_gap_bars_path"]
    if gap.exists():
        paths.append(gap)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the monitored daily drawdown-risk pipeline")
    parser.add_argument("--universe", choices=["sp500", "ndx", "sp400"], default="sp500")
    parser.add_argument("--as-of", help="Requested data cutoff in YYYY-MM-DD form")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "reports/operations/risk_signals",
    )
    parser.add_argument(
        "--registry-root",
        type=Path,
        default=PROJECT_ROOT / "reports/operations/model_registry",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    hazard_config = load_toml(PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml")
    operations = load_toml(PROJECT_ROOT / "configs/operations.toml")
    model, model_metadata, model_path = load_active_model(args.registry_root)
    if model_metadata["model_specification"] != operations["pipeline"]["model_specification"]:
        raise RuntimeError("Active model specification differs from operations configuration")
    paths = source_paths(args.universe, base_config)
    sources = {
        str(path.relative_to(PROJECT_ROOT)): file_sha256(path) for path in paths
    }
    data_fingerprint = content_digest(canonical_json_bytes(sources))
    loaders = {
        "sp500": lambda: load_sp500_panel(PROJECT_ROOT, base_config),
        "ndx": lambda: load_ndx_panel(PROJECT_ROOT),
        "sp400": lambda: load_sp400_panel(PROJECT_ROOT),
    }
    price, volume, membership = loaders[args.universe]()
    requested_as_of = (
        pd.Timestamp(args.as_of).normalize()
        if args.as_of
        else pd.Timestamp.today().normalize()
    )
    available_dates = price.index[price.index <= requested_as_of]
    if available_dates.empty:
        raise RuntimeError(f"No market data on or before requested date {requested_as_of.date()}")
    market_data_date = pd.Timestamp(available_dates.max()).normalize()
    price = price.loc[:market_data_date]
    volume = volume.loc[:market_data_date]
    membership = membership.loc[:market_data_date]
    result = score_and_monitor(
        price=price,
        volume=volume,
        membership=membership,
        requested_as_of=requested_as_of,
        market_data_date=market_data_date,
        model=model,
        base_config=base_config,
        hazard_config=hazard_config,
        operations_config=operations,
    )
    signals = result.signals
    health = result.health

    revision = git_revision()
    run_id = (
        f"{args.universe}_{market_data_date.date()}_"
        f"pipeline-{operations['pipeline']['version']}_code-{revision[:8]}_"
        f"model-{model_metadata['artifact_id'][-8:]}_data-{data_fingerprint[:8]}"
    )
    manifest = {
        "run_id": run_id,
        "pipeline_version": operations["pipeline"]["version"],
        "model_specification": operations["pipeline"]["model_specification"],
        "code_revision": revision,
        "universe": args.universe,
        "requested_as_of": str(requested_as_of.date()),
        "market_data_date": str(market_data_date.date()),
        "model_artifact_id": model_metadata["artifact_id"],
        "model_artifact_path": str(model_path),
        "model_sha256": model_metadata["model_sha256"],
        "training_last_episode_date": model_metadata["training_last_episode_date"],
        "training_episodes": model_metadata["training_episodes"],
        "feature_count": len(result.feature_columns),
        "feature_schema_sha256": feature_schema_digest(result.feature_columns),
        "source_sha256": sources,
        "source_fingerprint_sha256": data_fingerprint,
        "health_status": health["status"],
        "signals_authorized": health["signals_authorized"],
        "signals_emitted": len(signals),
    }
    output_path, reused = publish_atomic_run(
        args.output_root,
        run_id,
        signals=signals,
        health=health,
        manifest=manifest,
    )
    result = {
        "run_id": run_id,
        "output_path": str(output_path),
        "idempotent_retry": reused,
        "health_status": health["status"],
        "signals_authorized": health["signals_authorized"],
        "signals_emitted": len(signals),
        "market_data_date": str(market_data_date.date()),
    }
    print(json.dumps(result, indent=2))
    if health["status"] == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

