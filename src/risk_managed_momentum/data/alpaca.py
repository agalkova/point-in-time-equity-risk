from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

import pandas as pd
import requests


HISTORICAL_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
ALLOWED_ADJUSTMENTS = {"raw", "split", "dividend", "spin-off", "all"}


class AlpacaDataError(RuntimeError):
    """Raised when the historical market-data response is unusable."""


@dataclass(frozen=True)
class DownloadManifest:
    source: str
    endpoint: str
    feed: str
    timeframe: str
    adjustment: str
    start: str
    end: str
    requested_symbols: list[str]
    returned_symbols: list[str]
    missing_symbols: list[str]
    rows: int
    pages: int
    retrieved_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbols(symbols: Iterable[str]) -> list[str]:
    cleaned = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
    if not cleaned:
        raise ValueError("At least one symbol is required")
    invalid = [symbol for symbol in cleaned if "," in symbol or any(ch.isspace() for ch in symbol)]
    if invalid:
        raise ValueError(f"Invalid symbols: {invalid}")
    return cleaned


def normalize_bars(payload: dict[str, Any], adjustment: str, feed: str) -> pd.DataFrame:
    """Normalize one Alpaca multi-symbol bars response page."""
    bars = payload.get("bars")
    if bars is None or not isinstance(bars, dict):
        raise AlpacaDataError("Response does not contain a multi-symbol 'bars' mapping")

    rows: list[dict[str, Any]] = []
    for requested_ticker, ticker_bars in bars.items():
        if not isinstance(ticker_bars, list):
            raise AlpacaDataError(f"Bars for {requested_ticker} are not a list")
        for bar in ticker_bars:
            rows.append(
                {
                    "timestamp": bar.get("t"),
                    "date": str(bar.get("t", ""))[:10],
                    "ticker": requested_ticker,
                    "open": bar.get("o"),
                    "high": bar.get("h"),
                    "low": bar.get("l"),
                    "close": bar.get("c"),
                    "volume": bar.get("v"),
                    "trade_count": bar.get("n"),
                    "vwap": bar.get("vw"),
                    "feed": feed,
                    "adjustment": adjustment,
                    "source": "alpaca",
                }
            )
    columns = [
        "timestamp",
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "vwap",
        "feed",
        "adjustment",
        "source",
    ]
    return pd.DataFrame(rows, columns=columns)


class AlpacaHistoricalClient:
    """Small authenticated client for reproducible historical daily bars."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        endpoint: str = HISTORICAL_BARS_URL,
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
                "User-Agent": "risk-managed-momentum/0.1.0",
            }
        )

    @classmethod
    def from_environment(cls, **kwargs: Any) -> "AlpacaHistoricalClient":
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
            message = response.text[:500]
            raise AlpacaDataError(f"Alpaca HTTP {response.status_code}: {message}")
        raise AlpacaDataError("Alpaca request failed after retry limit")

    def download_daily_bars(
        self,
        symbols: Iterable[str],
        *,
        start: str | date,
        end: str | date,
        feed: str = "sip",
        adjustment: str = "raw",
        limit: int = 10_000,
        asof: str | date | None = None,
    ) -> tuple[pd.DataFrame, DownloadManifest]:
        requested = normalize_symbols(symbols)
        if feed != "sip":
            raise ValueError("This project requires feed='sip'; IEX volume is not comparable")
        if adjustment not in ALLOWED_ADJUSTMENTS:
            raise ValueError(f"Unsupported adjustment: {adjustment}")
        if not 1 <= limit <= 10_000:
            raise ValueError("Alpaca limit must be between 1 and 10,000")

        start_text = start.isoformat() if isinstance(start, date) else str(start)
        end_text = end.isoformat() if isinstance(end, date) else str(end)
        if date.fromisoformat(start_text[:10]) > date.fromisoformat(end_text[:10]):
            raise ValueError("Start date must not be after end date")

        params: dict[str, Any] = {
            "symbols": ",".join(requested),
            "timeframe": "1Day",
            "start": start_text,
            "end": end_text,
            "limit": limit,
            "adjustment": adjustment,
            "feed": feed,
            "sort": "asc",
        }
        if asof is not None:
            params["asof"] = asof.isoformat() if isinstance(asof, date) else str(asof)

        pages: list[pd.DataFrame] = []
        page_count = 0
        page_token: str | None = None
        while True:
            if page_token:
                params["page_token"] = page_token
            else:
                params.pop("page_token", None)
            payload = self._get(params)
            pages.append(normalize_bars(payload, adjustment=adjustment, feed=feed))
            page_count += 1
            page_token = payload.get("next_page_token")
            if not page_token:
                break

        frame = pd.concat(pages, ignore_index=True) if pages else pd.DataFrame()
        if not frame.empty:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
            frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.date
            frame = frame.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
            duplicate_count = int(frame.duplicated(["ticker", "timestamp"]).sum())
            if duplicate_count:
                raise AlpacaDataError(f"Received {duplicate_count} duplicate ticker-timestamp rows")
            invalid_ohlc = (
                (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
                | (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
            )
            if invalid_ohlc.any():
                raise AlpacaDataError(f"Received {int(invalid_ohlc.sum())} invalid OHLC rows")
            if (frame["volume"] < 0).any():
                raise AlpacaDataError("Received negative volume")

        returned = sorted(frame["ticker"].unique().tolist()) if not frame.empty else []
        manifest = DownloadManifest(
            source="alpaca",
            endpoint=self.endpoint,
            feed=feed,
            timeframe="1Day",
            adjustment=adjustment,
            start=start_text,
            end=end_text,
            requested_symbols=requested,
            returned_symbols=returned,
            missing_symbols=sorted(set(requested) - set(returned)),
            rows=int(len(frame)),
            pages=page_count,
            retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        return frame, manifest

    def download_daily_bars_batched(
        self,
        symbols: Iterable[str],
        *,
        start: str | date,
        end: str | date,
        feed: str = "sip",
        adjustment: str = "raw",
        limit: int = 10_000,
        asof: str | date | None = None,
        batch_size: int = 100,
    ) -> tuple[pd.DataFrame, DownloadManifest]:
        requested = normalize_symbols(symbols)
        if batch_size < 1:
            raise ValueError("Batch size must be positive")

        frames: list[pd.DataFrame] = []
        manifests: list[DownloadManifest] = []
        for offset in range(0, len(requested), batch_size):
            frame, manifest = self.download_daily_bars(
                requested[offset : offset + batch_size],
                start=start,
                end=end,
                feed=feed,
                adjustment=adjustment,
                limit=limit,
                asof=asof,
            )
            frames.append(frame)
            manifests.append(manifest)

        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if not combined.empty:
            combined = combined.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
            duplicate_count = int(combined.duplicated(["ticker", "timestamp"]).sum())
            if duplicate_count:
                raise AlpacaDataError(f"Received {duplicate_count} duplicate batched rows")
        returned = sorted(combined["ticker"].unique()) if not combined.empty else []
        first = manifests[0]
        manifest = DownloadManifest(
            source=first.source,
            endpoint=first.endpoint,
            feed=feed,
            timeframe=first.timeframe,
            adjustment=adjustment,
            start=first.start,
            end=first.end,
            requested_symbols=requested,
            returned_symbols=returned,
            missing_symbols=sorted(set(requested) - set(returned)),
            rows=int(len(combined)),
            pages=sum(item.pages for item in manifests),
            retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        return combined, manifest

