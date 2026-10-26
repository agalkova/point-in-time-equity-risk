from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.prospective import (
    append_ledger_entry,
    content_digest,
    write_immutable_frame,
    write_immutable_json,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append a frozen daily hazard prediction record")
    parser.add_argument("--run-path", type=Path)
    return parser.parse_args()


def choose_run(root: Path) -> Path:
    candidates = [path.parent for path in root.glob("sp500_*/manifest.json")]
    if not candidates:
        raise FileNotFoundError(f"No S&P 500 operation runs under {root}")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def main() -> None:
    args = parse_args()
    with (PROJECT_ROOT / "configs/prospective_hazard_v1.toml").open("rb") as handle:
        config = tomllib.load(handle)["record"]
    run_path = args.run_path or choose_run(PROJECT_ROOT / "reports/operations/risk_signals")
    if not run_path.is_absolute():
        run_path = (PROJECT_ROOT / run_path).resolve()
    manifest_path = run_path / "manifest.json"
    manifest_content = manifest_path.read_bytes()
    manifest = json.loads(manifest_content)
    signal_date = pd.Timestamp(manifest["market_data_date"]).normalize()
    start = pd.Timestamp(config["start_date"]).normalize()
    if signal_date < start:
        print(
            json.dumps(
                {
                    "status": "waiting_for_record_start",
                    "record_start": str(start.date()),
                    "latest_market_data_date": str(signal_date.date()),
                },
                indent=2,
            )
        )
        return
    if manifest["universe"] != config["universe"]:
        raise ValueError("Prospective source run has the wrong universe")
    if manifest["model_artifact_id"] != config["champion_artifact_id"]:
        raise ValueError("Active model differs from the frozen prospective champion")
    if manifest.get("shadow_model_artifact_id") != config["challenger_artifact_id"]:
        raise ValueError("Shadow model differs from the frozen prospective challenger")

    signals_path = run_path / "shadow_signals.csv"
    signals_content = signals_path.read_bytes()
    if content_digest(signals_content) != manifest["shadow_signals_sha256"]:
        raise ValueError("Shadow signal checksum differs from its operation manifest")
    signals = pd.read_csv(signals_path)
    evidence = PROJECT_ROOT / "reports/prospective/hazard" / str(signal_date.date())
    signals_digest = write_immutable_frame(evidence / "challenger_signals.csv", signals)
    evidence_manifest = {
        "record_version": config["version"],
        "signal_date": str(signal_date.date()),
        "champion_artifact_id": config["champion_artifact_id"],
        "challenger_artifact_id": config["challenger_artifact_id"],
        "source_run_id": manifest["run_id"],
        "source_manifest_sha256": content_digest(manifest_content),
        "challenger_signals_sha256": signals_digest,
        "episode_onsets": len(signals),
        "outcome_status": "pending",
    }
    evidence_digest = write_immutable_json(evidence / "manifest.json", evidence_manifest)
    append_ledger_entry(
        PROJECT_ROOT / "reports/prospective/hazard/ledger.csv",
        {
            "signal_date": str(signal_date.date()),
            "source_run_id": manifest["run_id"],
            "champion_artifact_id": config["champion_artifact_id"],
            "challenger_artifact_id": config["challenger_artifact_id"],
            "episode_onsets": len(signals),
            "signals_sha256": signals_digest,
            "manifest_sha256": evidence_digest,
            "outcome_status": "pending",
        },
    )
    print(json.dumps({"status": "recorded", **evidence_manifest}, indent=2))


if __name__ == "__main__":
    main()
