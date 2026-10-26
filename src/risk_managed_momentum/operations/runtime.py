from __future__ import annotations

import fcntl
import json
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import requests


class ConcurrentRunError(RuntimeError):
    """Raised when another operational run already holds the lock."""


@contextmanager
def exclusive_run_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ConcurrentRunError(f"Another operational run holds {path}") from error
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def send_webhook_alert(
    webhook_url: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: float = 10.0,
) -> None:
    if not webhook_url.startswith("https://"):
        raise ValueError("Alert webhook must use HTTPS")
    response = requests.post(
        webhook_url,
        data=json.dumps(payload, allow_nan=False),
        headers={"Content-Type": "application/json"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()


def send_macos_notification(title: str, message: str) -> None:
    script = (
        f"display notification {json.dumps(message[:500])} "
        f"with title {json.dumps(title[:100])}"
    )
    subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
