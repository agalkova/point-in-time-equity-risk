from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from risk_managed_momentum.operations.refresh import strict_json_bytes
from risk_managed_momentum.operations.runtime import (
    exclusive_run_lock,
    send_macos_notification,
    send_webhook_alert,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh data and run monitored daily inference")
    parser.add_argument("--universe", choices=["sp500"], default="sp500")
    parser.add_argument("--as-of", help="Historical replay date; omit for an actual daily run")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--alert-on-warn", action="store_true")
    return parser.parse_args()


def run_step(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": [Path(command[0]).name, *command[1:]],
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_last_json(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for offset, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, end = decoder.raw_decode(text[offset:])
        except json.JSONDecodeError:
            continue
        if not text[offset + end :].strip() and isinstance(value, dict):
            return value
    return None


def publish_receipt(payload: dict[str, Any]) -> Path:
    root = PROJECT_ROOT / "reports/operations/orchestrator"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = root / f"run_{stamp}_{os.getpid()}.json"
    with tempfile.NamedTemporaryFile(dir=root, delete=False) as handle:
        handle.write(strict_json_bytes(payload))
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return destination


def notify(webhook: str | None, event: dict[str, Any]) -> str | None:
    try:
        message = (
            f"risk-managed-momentum: {event['status']} "
            f"({event.get('stage', 'pipeline')})"
        )
        if webhook:
            send_webhook_alert(webhook, {"text": message, "event": event})
        elif platform.system() == "Darwin":
            send_macos_notification("Quant pipeline", message)
    except (OSError, requests.RequestException, subprocess.CalledProcessError, ValueError) as error:
        return f"{type(error).__name__}: {error}"
    return None


def main() -> None:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    webhook = os.environ.get("RMM_ALERT_WEBHOOK_URL")
    lock = PROJECT_ROOT / "reports/operations/.locks/daily-operations.lock"
    started = datetime.now(UTC).isoformat()
    steps: list[dict[str, Any]] = []
    with exclusive_run_lock(lock):
        if not args.skip_refresh:
            refresh_command = [sys.executable, "scripts/refresh_sp500_operations.py"]
            if args.as_of:
                refresh_command.extend(["--end", args.as_of])
            refresh = run_step(refresh_command)
            steps.append(refresh)
            if refresh["return_code"] != 0:
                event = {
                    "status": "FAIL",
                    "stage": "data_refresh",
                    "started_at_utc": started,
                    "completed_at_utc": datetime.now(UTC).isoformat(),
                    "steps": steps,
                }
                event["notification_error"] = notify(webhook, event)
                receipt = publish_receipt(event)
                print(json.dumps({"status": "FAIL", "receipt": str(receipt)}, indent=2))
                raise SystemExit(refresh["return_code"] or 1)

        pipeline_command = [
            sys.executable,
            "scripts/run_daily_risk_pipeline.py",
            "--universe",
            args.universe,
        ]
        if args.as_of:
            pipeline_command.extend(["--as-of", args.as_of])
        pipeline = run_step(pipeline_command)
        steps.append(pipeline)
        result = parse_last_json(pipeline["stdout"]) or {}
        health_status = result.get("health_status", "FAIL")
        status = "PASS" if pipeline["return_code"] == 0 else "FAIL"
        event = {
            "status": status,
            "health_status": health_status,
            "stage": "risk_pipeline",
            "started_at_utc": started,
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "pipeline_result": result,
            "steps": steps,
        }
        should_alert = status == "FAIL" or (args.alert_on_warn and health_status == "WARN")
        event["notification_error"] = notify(webhook if should_alert else None, event)
        receipt = publish_receipt(event)
        print(
            json.dumps(
                {
                    "status": status,
                    "health_status": health_status,
                    "receipt": str(receipt),
                    "pipeline_result": result,
                },
                indent=2,
            )
        )
        if pipeline["return_code"] != 0:
            raise SystemExit(pipeline["return_code"])


if __name__ == "__main__":
    main()
