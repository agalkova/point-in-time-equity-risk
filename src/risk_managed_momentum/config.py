from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "research.toml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the versioned research configuration."""
    config_path = Path(path)
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    @classmethod
    def from_mapping(cls, value: dict[str, str]) -> "DateRange":
        return cls(start=date.fromisoformat(value["start"]), end=date.fromisoformat(value["end"]))

    def validate(self) -> None:
        if self.start > self.end:
            raise ValueError(f"Invalid date range: {self.start} is after {self.end}")


def configured_ranges(config: dict[str, Any]) -> dict[str, DateRange]:
    ranges = {name: DateRange.from_mapping(value) for name, value in config["splits"].items()}
    for value in ranges.values():
        value.validate()
    return ranges

