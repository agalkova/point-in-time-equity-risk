from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_immutable(path: Path, content: bytes) -> str:
    """Create an immutable evidence file or verify an identical existing copy."""
    digest = content_digest(content)
    if path.exists():
        existing = path.read_bytes()
        if existing != content:
            raise FileExistsError(f"Prospective evidence already exists with different content: {path}")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
    return digest


def write_immutable_frame(path: Path, frame: pd.DataFrame) -> str:
    return write_immutable(path, csv_bytes(frame))


def write_immutable_json(path: Path, payload: dict[str, Any]) -> str:
    content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return write_immutable(path, content)


def append_ledger_entry(path: Path, entry: dict[str, Any]) -> None:
    """Append one unique signal-date record; never revise an existing observation."""
    incoming = pd.DataFrame([entry])
    if path.exists():
        ledger = pd.read_csv(path, dtype=str)
        duplicate = ledger[ledger["signal_date"].eq(str(entry["signal_date"]))]
        if not duplicate.empty:
            expected = incoming.astype(str).iloc[0].to_dict()
            actual = duplicate.iloc[0].to_dict()
            if actual != expected:
                raise FileExistsError(
                    f"Ledger already contains a different record for {entry['signal_date']}"
                )
            return
        ledger = pd.concat([ledger, incoming.astype(str)], ignore_index=True)
    else:
        ledger = incoming.astype(str)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(csv_bytes(ledger.sort_values("signal_date")))
    temporary.replace(path)
