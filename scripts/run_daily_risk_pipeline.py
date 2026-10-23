from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

import pandas as pd
from run_exuberance_hazard import load_modern_sp500, load_ndx, load_sp400

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import fit_hazard_model, predict_cumulative_risk
from risk_managed_momentum.operations.artifacts import publish_atomic_run
from risk_managed_momentum.operations.monitoring import build_health_report, file_sha256

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


def feature_schema_digest(feature_columns: list[str]) -> str:
    payload = json.dumps(feature_columns, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    hazard_config = load_toml(PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml")
    operations = load_toml(PROJECT_ROOT / "configs/operations.toml")
    legacy_price, legacy_volume = load_legacy_wide(
        PROJECT_ROOT / base_config["legacy_source"]["price_path"],
        PROJECT_ROOT / base_config["legacy_source"]["volume_path"],
    )
    legacy = build_exuberance_episode_dataset(
        legacy_price, legacy_volume, base_config, hazard_config
    )
    training = legacy.frame[legacy.frame["date"].between(
        hazard_config["training"]["start"], hazard_config["training"]["end"]
    )].copy()
    model = fit_hazard_model(
        training,
        legacy.feature_columns,
        hazard_config["outcome"]["horizon_end_days"],
        c=float(hazard_config["model"]["c"]),
        maximum_iterations=int(hazard_config["model"]["maximum_iterations"]),
        random_seed=int(hazard_config["project"]["random_seed"]),
    )
    reference = predict_cumulative_risk(model, training)

    loaders = {
        "sp500": lambda: load_modern_sp500(base_config),
        "ndx": load_ndx,
        "sp400": load_sp400,
    }
    price, volume, membership = loaders[args.universe]()
    requested_as_of = (
        pd.Timestamp(args.as_of).normalize()
        if args.as_of
        else pd.Timestamp(price.index.max()).normalize()
    )
    available_dates = price.index[price.index <= requested_as_of]
    if available_dates.empty:
        raise RuntimeError(f"No market data on or before requested date {requested_as_of.date()}")
    market_data_date = pd.Timestamp(available_dates.max()).normalize()
    price = price.loc[:market_data_date]
    volume = volume.loc[:market_data_date]
    membership = membership.loc[:market_data_date]
    live = build_exuberance_episode_dataset(
        price,
        volume,
        base_config,
        hazard_config,
        membership=membership,
        include_unlabeled=True,
    )
    if live.feature_columns != legacy.feature_columns:
        raise RuntimeError("Production feature schema differs from the frozen training schema")
    scored = predict_cumulative_risk(model, live.frame)
    recent_cutoff = market_data_date - pd.Timedelta(
        days=int(operations["pipeline"]["recent_monitoring_calendar_days"])
    )
    recent = scored[scored["date"].ge(recent_cutoff)].copy()
    health = build_health_report(
        requested_as_of=requested_as_of,
        market_data_date=market_data_date,
        price=price,
        membership=membership,
        reference_episodes=reference,
        recent_episodes=recent,
        feature_columns=live.feature_columns,
        score_column="risk_40",
        quality_config=operations["quality_gates"],
        drift_config=operations["drift"],
    )
    signal_columns = [
        "date",
        "ticker",
        "risk_10",
        "risk_20",
        "risk_40",
        "risk_60",
        "rank_ret_60",
        "rank_volatility_20",
        "rank_volume_z_20",
        "market_return_20",
        "market_breadth_20",
    ]
    signals = scored[scored["date"].eq(market_data_date)][signal_columns].copy()
    signals = signals.sort_values(["risk_40", "ticker"], ascending=[False, True])
    if not health["signals_authorized"]:
        signals = signals.iloc[0:0].copy()

    revision = git_revision()
    run_id = (
        f"{args.universe}_{market_data_date.date()}_"
        f"pipeline-{operations['pipeline']['version']}_code-{revision[:8]}"
    )
    sources = {
        str(path.relative_to(PROJECT_ROOT)): file_sha256(path)
        for path in source_paths(args.universe, base_config)
    }
    manifest = {
        "run_id": run_id,
        "pipeline_version": operations["pipeline"]["version"],
        "model_specification": operations["pipeline"]["model_specification"],
        "code_revision": revision,
        "universe": args.universe,
        "requested_as_of": str(requested_as_of.date()),
        "market_data_date": str(market_data_date.date()),
        "training_last_episode_date": str(training["date"].max().date()),
        "training_episodes": len(training),
        "feature_count": len(live.feature_columns),
        "feature_schema_sha256": feature_schema_digest(live.feature_columns),
        "source_sha256": sources,
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

