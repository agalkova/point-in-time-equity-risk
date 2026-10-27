from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from risk_managed_momentum.config import load_config
from risk_managed_momentum.features.build import build_research_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = PROJECT_ROOT / "data/example/synthetic_bars.csv"
OUTPUT_PATH = PROJECT_ROOT / "reports/example/synthetic_demo_summary.json"
REQUIRED_COLUMNS = {"date", "ticker", "open", "high", "low", "close", "volume", "source"}


def run_example() -> dict:
    bars = pd.read_csv(EXAMPLE_PATH, parse_dates=["date"])
    missing = REQUIRED_COLUMNS.difference(bars.columns)
    if missing:
        raise ValueError(f"Synthetic example is missing columns: {sorted(missing)}")
    if bars.duplicated(["date", "ticker"]).any():
        raise ValueError("Synthetic example contains duplicate date/ticker rows")
    if set(bars["source"].dropna().unique()) != {"synthetic"}:
        raise ValueError("Example data must be labeled synthetic")

    price = bars.pivot(index="date", columns="ticker", values="close")
    volume = bars.pivot(index="date", columns="ticker", values="volume")
    dataset = build_research_dataset(
        price,
        volume,
        load_config(PROJECT_ROOT / "configs/research.toml"),
    )
    frame = dataset.frame.sort_values("date").copy()
    split_date = frame["date"].quantile(0.70)
    train = frame[frame["date"].le(split_date)]
    test = frame[frame["date"].gt(split_date)]
    for name, sample in {"training": train, "test": test}.items():
        if len(sample) < 20 or sample["target"].nunique() != 2:
            raise RuntimeError(f"Synthetic {name} sample does not exercise both target classes")

    model = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=0.1,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(train[dataset.feature_columns], train["target"])
    score = model.predict_proba(test[dataset.feature_columns])[:, 1]
    prevalence = float(test["target"].mean())
    return {
        "purpose": "schema and pipeline demonstration only",
        "source": "deterministic synthetic data",
        "bars": len(bars),
        "securities": int(bars["ticker"].nunique()),
        "eligible_observations": len(frame),
        "training_observations": len(train),
        "test_observations": len(test),
        "test_events": int(test["target"].sum()),
        "test_prevalence": prevalence,
        "test_roc_auc": float(roc_auc_score(test["target"], score)),
        "test_average_precision": float(average_precision_score(test["target"], score)),
        "research_claim_supported": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the public synthetic pipeline demonstration")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and run without writing a report",
    )
    args = parser.parse_args()
    summary = run_example()
    if not args.check:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
