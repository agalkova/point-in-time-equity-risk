from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Protocol


class ObjectStore(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]: ...

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: dict[str, str],
    ) -> dict[str, Any]: ...


def canonical_json(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_sha256(path: Path) -> str:
    return content_sha256(path.read_bytes())


def deterministic_run_id(*, run_date: str, input_sha256: str, commit_sha: str) -> str:
    commit = commit_sha if commit_sha != "unknown" else "local"
    return f"synthetic-{run_date}-{input_sha256[:12]}-{commit[:8]}"


def build_run_bundle(
    output_root: Path,
    *,
    run_id: str,
    run_date: str,
    summary: dict[str, Any],
    input_sha256: str,
    commit_sha: str,
    image_uri: str,
) -> tuple[Path, bool]:
    """Create an immutable synthetic-run bundle or verify an identical retry."""
    summary_content = canonical_json(summary)
    health = {
        "status": "PASS",
        "checks": {
            "synthetic_source": summary.get("source") == "deterministic synthetic data",
            "no_research_claim": summary.get("research_claim_supported") is False,
            "both_target_classes": 0
            < int(summary.get("test_events", 0))
            < int(summary.get("test_observations", 0)),
        },
    }
    if not all(health["checks"].values()):
        raise RuntimeError(f"Synthetic validation failed: {health['checks']}")
    health_content = canonical_json(health)
    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_date_utc": run_date,
        "workload": "synthetic-demonstration",
        "commit_sha": commit_sha,
        "image_uri": image_uri,
        "input_sha256": input_sha256,
        "summary_sha256": content_sha256(summary_content),
        "health_sha256": content_sha256(health_content),
        "status": "PASS",
    }
    files = {
        "summary.json": summary_content,
        "health.json": health_content,
        "manifest.json": canonical_json(manifest),
    }
    final = output_root / run_id
    if final.exists():
        for name, expected in files.items():
            existing = final / name
            if not existing.exists() or existing.read_bytes() != expected:
                raise FileExistsError(f"Existing run differs from retry: {existing}")
        return final, True

    output_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{run_id}-", dir=output_root))
    try:
        for name, content in files.items():
            (temporary / name).write_bytes(content)
        os.replace(temporary, final)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return final, False


def _read_object(client: ObjectStore, bucket: str, key: str) -> bytes | None:
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception as error:
        response = getattr(error, "response", {})
        code = str(response.get("Error", {}).get("Code", ""))
        if code in {"NoSuchKey", "404", "NotFound"}:
            return None
        raise
    body = response["Body"]
    return body.read() if hasattr(body, "read") else bytes(body)


def publish_bundle(
    client: ObjectStore,
    *,
    bucket: str,
    prefix: str,
    bundle: Path,
) -> dict[str, str]:
    """Publish immutable run objects and a deterministic latest pointer to S3."""
    manifest = json.loads((bundle / "manifest.json").read_text())
    run_id = str(manifest["run_id"])
    base = f"{prefix.strip('/')}/runs/{run_id}".strip("/")
    published: dict[str, str] = {}
    for path in sorted(bundle.iterdir()):
        if not path.is_file():
            continue
        content = path.read_bytes()
        key = f"{base}/{path.name}"
        existing = _read_object(client, bucket, key)
        if existing is not None:
            if existing != content:
                raise FileExistsError(f"Existing S3 object differs from retry: s3://{bucket}/{key}")
        else:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType="application/json" if path.suffix == ".json" else "text/plain",
                Metadata={"sha256": content_sha256(content), "run-id": run_id},
            )
        published[path.name] = f"s3://{bucket}/{key}"

    latest = canonical_json(
        {
            "run_id": run_id,
            "run_date_utc": manifest["run_date_utc"],
            "status": manifest["status"],
            "manifest_uri": published["manifest.json"],
            "commit_sha": manifest["commit_sha"],
            "image_uri": manifest["image_uri"],
            "input_sha256": manifest["input_sha256"],
        }
    )
    latest_key = f"{prefix.strip('/')}/status/latest.json".strip("/")
    client.put_object(
        Bucket=bucket,
        Key=latest_key,
        Body=latest,
        ContentType="application/json",
        Metadata={"sha256": content_sha256(latest), "run-id": run_id},
    )
    published["latest.json"] = f"s3://{bucket}/{latest_key}"
    return published
