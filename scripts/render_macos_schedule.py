from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a macOS launchd schedule for daily inference")
    parser.add_argument("--hour", type=int, default=18)
    parser.add_argument("--minute", type=int, default=15)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports/operations/com.rmm.daily.plist",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 <= args.hour <= 23 or not 0 <= args.minute <= 59:
        raise ValueError("Schedule hour/minute is invalid")
    logs = PROJECT_ROOT / "reports/operations/logs"
    logs.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": "com.risk-managed-momentum.daily",
        "ProgramArguments": [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_scheduled_operations.py"),
            "--alert-on-warn",
        ],
        "WorkingDirectory": str(PROJECT_ROOT),
        "StartCalendarInterval": [
            {"Weekday": weekday, "Hour": args.hour, "Minute": args.minute}
            for weekday in range(1, 6)
        ],
        "StandardOutPath": str(logs / "daily.stdout.log"),
        "StandardErrorPath": str(logs / "daily.stderr.log"),
        "ProcessType": "Background",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(plistlib.dumps(payload, sort_keys=True))
    print(f"Rendered {args.output}")
    print("Review it, then copy it to ~/Library/LaunchAgents/ to enable the schedule.")


if __name__ == "__main__":
    main()
