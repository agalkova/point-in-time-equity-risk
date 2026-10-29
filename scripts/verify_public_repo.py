from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DATA_FILES = {
    "data/example/README.md",
    "data/example/synthetic_bars.csv",
    "data/external/.gitkeep",
    "data/interim/.gitkeep",
    "data/processed/.gitkeep",
    "data/raw/.gitkeep",
    "data/reference/.gitkeep",
}
REQUIRED_FILES = {
    "LICENSE",
    "Makefile",
    "README.md",
    "pyproject.toml",
    ".github/workflows/deploy-aws.yml",
    ".github/workflows/tests.yml",
    "Dockerfile",
    "docs/AWS_DEPLOYMENT.md",
    "docs/RESULTS.md",
    "docs/SP400_REPLICATION_RESULTS.md",
    "docs/POINT_IN_TIME_FUNDAMENTAL_RESULTS.md",
    "docs/RESUME_BULLETS.md",
    "data/example/synthetic_bars.csv",
}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MAX_PUBLIC_FILE_BYTES = 2_000_000


def public_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def main() -> None:
    tracked = public_files()
    failures: list[str] = []
    missing = sorted(REQUIRED_FILES.difference(tracked))
    if missing:
        failures.append(f"required public files are not tracked: {missing}")

    prohibited_data = sorted(
        path
        for path in tracked
        if path.startswith(("data/raw/", "data/interim/", "data/processed/", "data/external/"))
        and path not in ALLOWED_DATA_FILES
    )
    if prohibited_data:
        failures.append(f"vendor or derived data is tracked: {prohibited_data}")

    prohibited_names = sorted(
        path
        for path in tracked
        if Path(path).name in {".env", "credentials.json", "secrets.json"}
        or path.endswith((".pem", ".key"))
    )
    if prohibited_names:
        failures.append(f"credential-like files are tracked: {prohibited_names}")

    oversized = sorted(
        path
        for path in tracked
        if (PROJECT_ROOT / path).is_file()
        and (PROJECT_ROOT / path).stat().st_size > MAX_PUBLIC_FILE_BYTES
    )
    if oversized:
        failures.append(f"public files exceed {MAX_PUBLIC_FILE_BYTES:,} bytes: {oversized}")

    readme = (PROJECT_ROOT / "README.md").read_text()
    broken_links = []
    for target in MARKDOWN_LINK.findall(readme):
        if target.startswith(("http://", "https://", "#")):
            continue
        local_target = target.split("#", 1)[0]
        if local_target and not (PROJECT_ROOT / local_target).exists():
            broken_links.append(target)
    if broken_links:
        failures.append(f"README contains broken local links: {sorted(broken_links)}")
    if "/Users/" in readme:
        failures.append("README contains a machine-specific absolute path")
    if "-----BEGIN PRIVATE KEY-----" in readme:
        failures.append("README contains a private-key header")

    synthetic_failures: list[str] = []
    bars = pd.read_csv(PROJECT_ROOT / "data/example/synthetic_bars.csv")
    required_columns = {"date", "ticker", "open", "high", "low", "close", "volume", "source"}
    if missing_columns := sorted(required_columns.difference(bars.columns)):
        synthetic_failures.append(f"synthetic example is missing columns: {missing_columns}")
    if bars.duplicated(["date", "ticker"]).any():
        synthetic_failures.append("synthetic example contains duplicate date/ticker rows")
    if set(bars["source"].dropna().unique()) != {"synthetic"}:
        synthetic_failures.append("example rows are not exclusively labeled synthetic")
    failures.extend(synthetic_failures)

    report = {
        "status": "FAIL" if failures else "PASS",
        "public_files": len(tracked),
        "synthetic_rows": len(bars),
        "checks": {
            "required_files": not missing,
            "no_vendor_or_derived_data": not prohibited_data,
            "no_credential_files": not prohibited_names,
            "public_file_size_limit": not oversized,
            "readme_local_links": not broken_links,
            "readme_is_portable": "/Users/" not in readme,
            "synthetic_schema": not synthetic_failures,
        },
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
