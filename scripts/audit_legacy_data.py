from __future__ import annotations

import json
from pathlib import Path

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import audit_legacy_wide, load_legacy_wide


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    price, volume = load_legacy_wide(
        config["legacy_source"]["price_path"],
        config["legacy_source"]["volume_path"],
    )
    audit = audit_legacy_wide(price, volume)
    output = PROJECT_ROOT / "reports" / "tables" / "legacy_data_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit.to_dict(), indent=2) + "\n")
    print(json.dumps(audit.to_dict(), indent=2))


if __name__ == "__main__":
    main()

