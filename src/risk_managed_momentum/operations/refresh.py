from __future__ import annotations

import gzip
import io
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from risk_managed_momentum.data.panel import build_point_in_time_panel


def _write_csv(frame: pd.DataFrame, path: Path, options: dict[str, Any]) -> None:
    compression = options.get("compression")
    if isinstance(compression, dict) and compression.get("method") == "gzip":
        gzip_options = dict(compression)
        gzip_options.pop("method")
        csv_options = {key: value for key, value in options.items() if key != "compression"}
        with (
            path.open("wb") as raw,
            gzip.GzipFile(filename="", fileobj=raw, mode="wb", **gzip_options) as compressed,
            io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
        ):
            frame.to_csv(text, index=False, **csv_options)
        return
    frame.to_csv(path, index=False, **options)


def merge_bar_history(
    existing: pd.DataFrame,
    incoming: pd.DataFrame,
    *,
    replace_from: pd.Timestamp,
) -> pd.DataFrame:
    """Replace a recent overlap window while preserving older validated history."""
    if set(existing.columns) != set(incoming.columns):
        missing = sorted(set(existing.columns) - set(incoming.columns))
        extra = sorted(set(incoming.columns) - set(existing.columns))
        raise ValueError(f"Bar schema mismatch; missing={missing}, extra={extra}")
    existing = existing.copy()
    incoming = incoming[existing.columns].copy()
    existing["date"] = pd.to_datetime(existing["date"], errors="raise").dt.normalize()
    incoming["date"] = pd.to_datetime(incoming["date"], errors="raise").dt.normalize()
    retained = existing[existing["date"].lt(replace_from.normalize())]
    merged = pd.concat([retained, incoming], ignore_index=True)
    duplicate_count = int(merged.duplicated(["ticker", "date"]).sum())
    if duplicate_count:
        raise ValueError(f"Merged bars contain {duplicate_count} duplicate ticker-date rows")
    merged["timestamp"] = pd.to_datetime(merged["timestamp"], utc=True, errors="raise")
    return merged.sort_values(["ticker", "timestamp"]).reset_index(drop=True)


def validate_operational_panel(
    bars: pd.DataFrame,
    alias_bars: pd.DataFrame,
    membership: pd.DataFrame,
    aliases: list[dict[str, Any]],
    *,
    minimum_latest_coverage: float,
) -> dict[str, Any]:
    price, _, member = build_point_in_time_panel(
        pd.concat([bars, alias_bars[bars.columns]], ignore_index=True),
        membership,
        aliases,
    )
    if price.empty:
        raise ValueError("Refreshed panel is empty")
    latest = pd.Timestamp(price.index.max()).normalize()
    latest_members = member.loc[latest].astype(bool)
    member_tickers = latest_members.index[latest_members]
    coverage = float(price.loc[latest, member_tickers].notna().mean())
    if coverage < minimum_latest_coverage:
        raise ValueError(
            f"Latest member price coverage {coverage:.3f} is below "
            f"{minimum_latest_coverage:.3f}"
        )
    return {
        "market_data_date": str(latest.date()),
        "latest_members": int(latest_members.sum()),
        "latest_membership_price_coverage": coverage,
        "trading_days": len(price),
    }


def atomic_write_dataframes(
    replacements: dict[Path, pd.DataFrame],
    *,
    csv_options: dict[Path, dict[str, Any]] | None = None,
) -> None:
    """Serialize all replacements first, then swap them with rollback on failure."""
    if not replacements:
        return
    csv_options = csv_options or {}
    transaction_id = uuid.uuid4().hex
    staged: list[tuple[Path, Path]] = []
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    committed = False
    try:
        for destination, frame in replacements.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix=f".{destination.name}.stage-",
                dir=destination.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
            options = csv_options.get(destination, {})
            _write_csv(frame, temporary, options)
            staged.append((temporary, destination))
        for temporary, destination in staged:
            if destination.exists():
                backup = destination.with_name(
                    f".{destination.name}.backup-{transaction_id}"
                )
                os.replace(destination, backup)
                backups[destination] = backup
            os.replace(temporary, destination)
            installed.append(destination)
        committed = True
    except Exception:
        for destination in reversed(installed):
            destination.unlink(missing_ok=True)
        for destination, backup in backups.items():
            if backup.exists():
                os.replace(backup, destination)
        raise
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        if committed:
            for backup in backups.values():
                backup.unlink(missing_ok=True)


def strict_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
