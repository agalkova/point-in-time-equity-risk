from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from run_example_pipeline import EXAMPLE_PATH, run_example

from risk_managed_momentum.operations.cloud import (
    build_run_bundle,
    deterministic_run_id,
    file_sha256,
    publish_bundle,
)


def log(level: str, event: str, **fields: object) -> None:
    print(
        json.dumps(
            {"level": level, "event": event, **fields},
            sort_keys=True,
            allow_nan=False,
        ),
        flush=True,
    )


def main() -> None:
    run_date = os.environ.get("RUN_DATE_UTC") or datetime.now(UTC).date().isoformat()
    commit_sha = os.environ.get("GIT_COMMIT_SHA", "unknown")
    image_uri = os.environ.get("IMAGE_URI", "local")
    output_root = Path(os.environ.get("OUTPUT_ROOT", "reports/cloud"))
    input_sha256 = file_sha256(EXAMPLE_PATH)
    run_id = deterministic_run_id(
        run_date=run_date,
        input_sha256=input_sha256,
        commit_sha=commit_sha,
    )
    log("INFO", "run_started", run_id=run_id, run_date_utc=run_date)
    summary = run_example()
    bundle, reused = build_run_bundle(
        output_root,
        run_id=run_id,
        run_date=run_date,
        summary=summary,
        input_sha256=input_sha256,
        commit_sha=commit_sha,
        image_uri=image_uri,
    )
    log("INFO", "bundle_ready", run_id=run_id, path=str(bundle), reused=reused)

    bucket = os.environ.get("ARTIFACT_BUCKET")
    if bucket:
        import boto3

        published = publish_bundle(
            boto3.client("s3"),
            bucket=bucket,
            prefix=os.environ.get("ARTIFACT_PREFIX", "synthetic"),
            bundle=bundle,
        )
        log("INFO", "bundle_published", run_id=run_id, objects=published)
    else:
        log("INFO", "publication_skipped", run_id=run_id, reason="ARTIFACT_BUCKET not set")
    log("INFO", "run_completed", run_id=run_id, status="PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 - batch boundary must emit a structured failure
        log("ERROR", "run_failed", error_type=type(error).__name__, message=str(error))
        sys.exit(1)
