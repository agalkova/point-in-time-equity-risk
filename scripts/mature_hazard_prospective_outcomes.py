from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.universes import load_sp500_panel
from risk_managed_momentum.prospective import append_ledger_entry, write_immutable_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HORIZONS = (10, 20, 40, 60)
THRESHOLD = -0.15


def main() -> None:
    root = PROJECT_ROOT / "reports/prospective/hazard"
    evidence_dirs = sorted(path for path in root.glob("????-??-??") if path.is_dir())
    pending = [path for path in evidence_dirs if not (path / "outcomes.csv").exists()]
    if not pending:
        print(json.dumps({"status": "no_pending_prospective_outcomes"}, indent=2))
        return

    price, _, _ = load_sp500_panel(
        PROJECT_ROOT, load_config(PROJECT_ROOT / "configs/research.toml")
    )
    positions = pd.Series(range(len(price.index)), index=price.index)
    matured = []
    still_pending = []
    for evidence in pending:
        signal_date = pd.Timestamp(evidence.name)
        if signal_date not in positions or int(positions[signal_date]) + max(HORIZONS) >= len(
            price
        ):
            still_pending.append(evidence.name)
            continue
        signals = pd.read_csv(evidence / "challenger_signals.csv")
        rows = []
        unresolved = False
        position = int(positions[signal_date])
        for signal in signals.itertuples(index=False):
            if signal.ticker not in price or pd.isna(price.loc[signal_date, signal.ticker]):
                unresolved = True
                break
            baseline = float(price.loc[signal_date, signal.ticker])
            future = price.iloc[position + 1 : position + 1 + max(HORIZONS)][signal.ticker]
            if len(future) < max(HORIZONS) or future.isna().any():
                unresolved = True
                break
            returns = future.div(baseline).sub(1.0)
            row = {
                "signal_date": evidence.name,
                "ticker": signal.ticker,
                "baseline_price": baseline,
                "minimum_return_60": float(returns.min()),
            }
            for horizon in HORIZONS:
                row[f"target_{horizon}"] = int(returns.iloc[:horizon].min() <= THRESHOLD)
                row[f"realized_minimum_return_{horizon}"] = float(returns.iloc[:horizon].min())
            rows.append(row)
        if unresolved:
            still_pending.append(evidence.name)
            continue
        columns = [
            "signal_date",
            "ticker",
            "baseline_price",
            "minimum_return_60",
            *[
                item
                for horizon in HORIZONS
                for item in (f"target_{horizon}", f"realized_minimum_return_{horizon}")
            ],
        ]
        outcomes = pd.DataFrame(rows, columns=columns)
        digest = write_immutable_frame(evidence / "outcomes.csv", outcomes)
        append_ledger_entry(
            root / "outcome_ledger.csv",
            {
                "signal_date": evidence.name,
                "mature_episodes": len(outcomes),
                "events_60": int(outcomes["target_60"].sum()) if len(outcomes) else 0,
                "outcomes_sha256": digest,
                "outcome_status": "mature",
            },
        )
        matured.append(evidence.name)
    print(
        json.dumps(
            {
                "status": "outcome_refresh_complete",
                "newly_matured_signal_dates": matured,
                "still_pending_signal_dates": still_pending,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
