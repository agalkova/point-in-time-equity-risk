from __future__ import annotations

import os
import time
import tomllib
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
import requests

from risk_managed_momentum.data.alpaca import AlpacaDataError, normalize_symbols

CORPORATE_ACTIONS_URL = "https://data.alpaca.markets/v1/corporate-actions"


def load_corporate_action_overrides(path: str | os.PathLike[str]) -> pd.DataFrame:
    """Load explicitly sourced terminal-action repairs from a reviewable TOML file."""
    with open(path, "rb") as handle:
        payload = tomllib.load(handle)
    rows = payload.get("action", [])
    if not rows:
        return pd.DataFrame(columns=["action_type", "action_symbol", "action_date"])
    frame = pd.DataFrame(rows)
    frame["action_symbol"] = frame["action_symbol"].astype(str).str.upper()
    frame["action_date"] = pd.to_datetime(frame["action_date"], errors="raise").dt.date
    return frame


@dataclass(frozen=True)
class CorporateActionManifest:
    source: str
    endpoint: str
    start: str
    end: str
    requested_symbols: list[str]
    action_types: list[str]
    rows: int
    pages: int
    retrieved_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_corporate_actions(payload: dict[str, Any]) -> pd.DataFrame:
    """Flatten one categorized Alpaca corporate-actions response page."""
    grouped = payload.get("corporate_actions")
    if grouped is None or not isinstance(grouped, dict):
        raise AlpacaDataError("Response does not contain a corporate_actions mapping")
    rows: list[dict[str, Any]] = []
    for action_type, actions in grouped.items():
        if not isinstance(actions, list):
            raise AlpacaDataError(f"Corporate actions for {action_type} are not a list")
        for action in actions:
            if not isinstance(action, dict):
                raise AlpacaDataError(f"Corporate action in {action_type} is not an object")
            row = dict(action)
            row["action_type"] = str(action_type)
            row["action_symbol"] = str(
                action.get("acquiree_symbol")
                or action.get("old_symbol")
                or action.get("symbol")
                or ""
            ).upper()
            row["action_date"] = (
                action.get("effective_date") or action.get("ex_date") or action.get("process_date")
            )
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["action_type", "action_symbol", "action_date"])
    frame = pd.DataFrame(rows)
    for column in [name for name in frame.columns if name.endswith("_date")]:
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.date
    order = ["action_date", "action_symbol", "action_type"]
    remaining = sorted(set(frame.columns) - set(order))
    return frame[order + remaining].sort_values(order).reset_index(drop=True)


class AlpacaCorporateActionsClient:
    """Authenticated, paginated client for Alpaca's corporate-action history."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        endpoint: str = CORPORATE_ACTIONS_URL,
        timeout_seconds: float = 30.0,
        max_retries: int = 5,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("Alpaca API key and secret are required")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
                "User-Agent": "risk-managed-momentum/0.3.0",
            }
        )

    @classmethod
    def from_environment(cls, **kwargs: Any) -> AlpacaCorporateActionsClient:
        return cls(
            os.environ.get("APCA_API_KEY_ID", ""),
            os.environ.get("APCA_API_SECRET_KEY", ""),
            **kwargs,
        )

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            response = self.session.get(self.endpoint, params=params, timeout=self.timeout_seconds)
            if response.status_code == 200:
                payload = response.json()
                if not isinstance(payload, dict):
                    raise AlpacaDataError("Alpaca returned a non-object JSON response")
                return payload
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 30)
                time.sleep(delay)
                continue
            raise AlpacaDataError(f"Alpaca HTTP {response.status_code}: {response.text[:500]}")
        raise AlpacaDataError("Alpaca request failed after retry limit")

    def download(
        self,
        symbols: Iterable[str],
        *,
        start: str | date,
        end: str | date,
        batch_size: int = 100,
        limit: int = 1_000,
    ) -> tuple[pd.DataFrame, CorporateActionManifest]:
        requested = normalize_symbols(symbols)
        if batch_size < 1:
            raise ValueError("Batch size must be positive")
        start_text = start.isoformat() if isinstance(start, date) else str(start)
        end_text = end.isoformat() if isinstance(end, date) else str(end)
        if date.fromisoformat(start_text[:10]) > date.fromisoformat(end_text[:10]):
            raise ValueError("Start date must not be after end")

        frames: list[pd.DataFrame] = []
        pages = 0
        for offset in range(0, len(requested), batch_size):
            params: dict[str, Any] = {
                "symbols": ",".join(requested[offset : offset + batch_size]),
                "start": start_text,
                "end": end_text,
                "limit": int(limit),
            }
            page_token: str | None = None
            while True:
                if page_token:
                    params["page_token"] = page_token
                else:
                    params.pop("page_token", None)
                payload = self._get(params)
                frames.append(normalize_corporate_actions(payload))
                pages += 1
                page_token = payload.get("next_page_token")
                if not page_token:
                    break

        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if not frame.empty:
            dedupe = [column for column in ["id", "action_type"] if column in frame.columns]
            frame = (
                frame.drop_duplicates(dedupe or None)
                .sort_values(["action_date", "action_symbol", "action_type"])
                .reset_index(drop=True)
            )
        manifest = CorporateActionManifest(
            source="alpaca",
            endpoint=self.endpoint,
            start=start_text,
            end=end_text,
            requested_symbols=requested,
            action_types=sorted(frame["action_type"].unique()) if not frame.empty else [],
            rows=len(frame),
            pages=pages,
            retrieved_at_utc=datetime.now(UTC).isoformat(),
        )
        return frame, manifest
