from __future__ import annotations

import hashlib
import io
import json
import tempfile
from pathlib import Path
from typing import Any

import joblib

from risk_managed_momentum.models.hazard import FittedHazardModel
from risk_managed_momentum.prospective import content_digest


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def feature_schema_digest(feature_columns: list[str]) -> str:
    content = json.dumps(feature_columns, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def register_model_artifact(
    registry_root: Path,
    fitted: FittedHazardModel,
    metadata: dict[str, Any],
) -> tuple[Path, bool]:
    """Register an immutable fitted model and integrity metadata."""
    identity = {
        "model_specification": metadata["model_specification"],
        "training_data_sha256": metadata["training_data_sha256"],
        "training_config_sha256": metadata["training_config_sha256"],
        "feature_schema_sha256": feature_schema_digest(fitted.feature_columns),
        "horizons": fitted.horizons,
    }
    identity_digest = content_digest(canonical_json_bytes(identity))
    artifact_id = f"hazard-{metadata['model_specification']}-{identity_digest[:16]}"
    artifact_path = registry_root / artifact_id

    model_buffer = io.BytesIO()
    joblib.dump(fitted, model_buffer, compress=3)
    model_content = model_buffer.getvalue()
    complete_metadata = {
        **metadata,
        **identity,
        "artifact_id": artifact_id,
        "model_sha256": content_digest(model_content),
        "feature_columns": fitted.feature_columns,
        "interval_feature_columns": fitted.interval_feature_columns,
    }
    metadata_content = canonical_json_bytes(complete_metadata)
    if artifact_path.exists():
        expected = {
            "model.joblib": model_content,
            "metadata.json": metadata_content,
        }
        for name, content in expected.items():
            path = artifact_path / name
            if not path.exists() or path.read_bytes() != content:
                raise FileExistsError(f"Registered model artifact differs: {path}")
        return artifact_path, True

    registry_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}-", dir=registry_root))
    try:
        (temporary / "model.joblib").write_bytes(model_content)
        (temporary / "metadata.json").write_bytes(metadata_content)
        temporary.replace(artifact_path)
    except Exception:
        for child in temporary.glob("*"):
            child.unlink(missing_ok=True)
        temporary.rmdir()
        raise
    return artifact_path, False


def activate_model(registry_root: Path, artifact_id: str) -> Path:
    return set_model_pointer(registry_root, artifact_id, "ACTIVE")


def set_model_pointer(registry_root: Path, artifact_id: str, pointer_name: str) -> Path:
    if not pointer_name or not pointer_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid model pointer name: {pointer_name!r}")
    pointer_name = pointer_name.upper()
    artifact_path = registry_root / artifact_id
    if not artifact_path.is_dir():
        raise FileNotFoundError(f"Cannot activate missing model artifact: {artifact_path}")
    pointer = registry_root / pointer_name
    content = (artifact_id + "\n").encode("utf-8")
    temporary = registry_root / f".{pointer_name}.tmp"
    temporary.write_bytes(content)
    temporary.replace(pointer)
    return pointer


def load_model_artifact(artifact_path: Path) -> tuple[FittedHazardModel, dict[str, Any]]:
    metadata_path = artifact_path / "metadata.json"
    model_path = artifact_path / "model.joblib"
    metadata = json.loads(metadata_path.read_text())
    model_content = model_path.read_bytes()
    if content_digest(model_content) != metadata["model_sha256"]:
        raise ValueError(f"Model checksum mismatch: {model_path}")
    fitted = joblib.load(io.BytesIO(model_content))
    if not isinstance(fitted, FittedHazardModel):
        raise TypeError(f"Unexpected model artifact type: {type(fitted)!r}")
    if feature_schema_digest(fitted.feature_columns) != metadata["feature_schema_sha256"]:
        raise ValueError("Model feature schema does not match registered metadata")
    if fitted.horizons != metadata["horizons"]:
        raise ValueError("Model horizons do not match registered metadata")
    return fitted, metadata


def load_active_model(registry_root: Path) -> tuple[FittedHazardModel, dict[str, Any], Path]:
    return load_model_pointer(registry_root, "ACTIVE")


def load_model_pointer(
    registry_root: Path,
    pointer_name: str,
) -> tuple[FittedHazardModel, dict[str, Any], Path]:
    pointer_name = pointer_name.upper()
    pointer = registry_root / pointer_name
    if not pointer.exists():
        raise FileNotFoundError(f"No {pointer_name} model pointer at {pointer}")
    artifact_id = pointer.read_text().strip()
    artifact_path = registry_root / artifact_id
    fitted, metadata = load_model_artifact(artifact_path)
    if metadata["artifact_id"] != artifact_id:
        raise ValueError(f"{pointer_name} pointer and model metadata artifact IDs differ")
    return fitted, metadata, artifact_path

