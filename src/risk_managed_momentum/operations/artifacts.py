from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from risk_managed_momentum.prospective import content_digest, csv_bytes


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def publish_atomic_run(
    output_root: Path,
    run_id: str,
    *,
    signals: pd.DataFrame,
    health: dict[str, Any],
    manifest: dict[str, Any],
    shadow_signals: pd.DataFrame | None = None,
) -> tuple[Path, bool]:
    """Atomically publish a deterministic run, or verify an identical retry."""
    signal_content = csv_bytes(signals)
    health_content = _json_bytes(health)
    complete_manifest = {
        **manifest,
        "signals_sha256": content_digest(signal_content),
        "health_sha256": content_digest(health_content),
    }
    shadow_content = csv_bytes(shadow_signals) if shadow_signals is not None else None
    if shadow_content is not None:
        complete_manifest["shadow_signals_sha256"] = content_digest(shadow_content)
    manifest_content = _json_bytes(complete_manifest)
    files = {
        "signals.csv": signal_content,
        "health.json": health_content,
        "manifest.json": manifest_content,
    }
    if shadow_content is not None:
        files["shadow_signals.csv"] = shadow_content
    final = output_root / run_id
    if final.exists():
        for name, expected in files.items():
            path = final / name
            if not path.exists() or path.read_bytes() != expected:
                raise FileExistsError(f"Existing run differs from deterministic retry: {path}")
        return final, True

    output_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{run_id}-", dir=output_root))
    try:
        for name, content in files.items():
            (temporary / name).write_bytes(content)
        temporary.replace(final)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return final, False

