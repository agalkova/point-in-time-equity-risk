from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "research.toml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the versioned research configuration."""
    config_path = Path(path).resolve()
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    project_root = config_path.parent.parent
    overrides = {
        ("legacy_source", "price_path"): os.environ.get("RMM_LEGACY_PRICE_PATH"),
        ("legacy_source", "volume_path"): os.environ.get("RMM_LEGACY_VOLUME_PATH"),
    }
    for section in ["legacy_source", "modern_source"]:
        for key, value in config.get(section, {}).items():
            if not key.endswith("_path"):
                continue
            override = overrides.get((section, key))
            configured = Path(override or value)
            config[section][key] = str(
                configured if configured.is_absolute() else project_root / configured
            )
    return config


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

