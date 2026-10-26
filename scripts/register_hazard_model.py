from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import fit_hazard_model
from risk_managed_momentum.operations.monitoring import file_sha256
from risk_managed_momentum.operations.registry import activate_model, register_model_artifact

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and register the frozen hazard model")
    parser.add_argument(
        "--registry-root",
        type=Path,
        default=PROJECT_ROOT / "reports/operations/model_registry",
    )
    parser.add_argument("--activate", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_path = PROJECT_ROOT / "configs/research.toml"
    hazard_path = PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml"
    base_config = load_config(base_path)
    hazard_config = load_toml(hazard_path)
    price_path = PROJECT_ROOT / base_config["legacy_source"]["price_path"]
    volume_path = PROJECT_ROOT / base_config["legacy_source"]["volume_path"]
    price, volume = load_legacy_wide(price_path, volume_path)
    dataset = build_exuberance_episode_dataset(price, volume, base_config, hazard_config)
    training = dataset.frame[dataset.frame["date"].between(
        hazard_config["training"]["start"], hazard_config["training"]["end"]
    )].copy()
    fitted = fit_hazard_model(
        training,
        dataset.feature_columns,
        hazard_config["outcome"]["horizon_end_days"],
        c=float(hazard_config["model"]["c"]),
        maximum_iterations=int(hazard_config["model"]["maximum_iterations"]),
        random_seed=int(hazard_config["project"]["random_seed"]),
    )
    training_hashes = {
        str(price_path.relative_to(PROJECT_ROOT)): file_sha256(price_path),
        str(volume_path.relative_to(PROJECT_ROOT)): file_sha256(volume_path),
    }
    training_data_digest = hashlib.sha256(
        json.dumps(training_hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()
    config_hashes = {
        str(base_path.relative_to(PROJECT_ROOT)): file_sha256(base_path),
        str(hazard_path.relative_to(PROJECT_ROOT)): file_sha256(hazard_path),
    }
    training_config_digest = hashlib.sha256(
        json.dumps(config_hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    artifact_path, reused = register_model_artifact(
        args.registry_root,
        fitted,
        {
            "model_specification": hazard_config["project"]["specification_version"],
            "training_data_sha256": training_data_digest,
            "training_source_sha256": training_hashes,
            "training_config_sha256": training_config_digest,
            "training_config_files_sha256": config_hashes,
            "training_first_episode_date": str(training["date"].min().date()),
            "training_last_episode_date": str(training["date"].max().date()),
            "training_episodes": len(training),
            "training_events_60": int(training["target_60"].sum()),
            "registered_from_code_revision": revision,
        },
    )
    if args.activate:
        activate_model(args.registry_root, artifact_path.name)
    print(
        json.dumps(
            {
                "artifact_id": artifact_path.name,
                "artifact_path": str(artifact_path),
                "idempotent_registration": reused,
                "activated": bool(args.activate),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

