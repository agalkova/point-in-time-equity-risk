from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.panel import build_point_in_time_panel
from risk_managed_momentum.features.alpha import build_alpha_dataset
from risk_managed_momentum.models.alpha import alpha_model_factories

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DATE = pd.Timestamp("2026-10-22")


def load_alpha_config() -> dict:
    with (PROJECT_ROOT / "configs" / "research_v0_3_alpha.toml").open("rb") as handle:
        return tomllib.load(handle)


def load_modern_panel(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = config["modern_source"]
    bars = pd.read_csv(source["bars_path"])
    aliases = pd.read_csv(source["historical_alias_bars_path"])
    bars = pd.concat([bars, aliases[bars.columns]], ignore_index=True)
    membership = pd.read_csv(source["membership_path"])
    with Path(source["aliases_path"]).open("rb") as handle:
        ticker_aliases = tomllib.load(handle)["alias"]
    return build_point_in_time_panel(bars, membership, ticker_aliases)


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    alpha_config = load_alpha_config()
    price, volume, membership = load_modern_panel(base_config)
    dataset = build_alpha_dataset(
        price,
        volume,
        base_config,
        alpha_config,
        membership,
        include_unlabeled=True,
    )
    frame = dataset.frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    signal_date = pd.Timestamp(frame["date"].max())
    train = frame[
        frame["future_residual_return_21"].notna() & frame["date"].lt(signal_date)
    ].copy()
    signal = frame[frame["date"].eq(signal_date)].copy()
    if train.empty or signal.empty:
        raise RuntimeError("Insufficient labeled history or no latest signal cross-section")

    ridge = alpha_model_factories(alpha_config)["ridge"]
    ridge.fit(train[dataset.feature_columns], train["future_residual_return_21"])
    signal["predicted_residual_return"] = ridge.predict(signal[dataset.feature_columns])
    signal["alpha_rank"] = signal["predicted_residual_return"].rank(
        method="average", pct=True
    )
    top_n = int(alpha_config["portfolio"]["top_n"])
    selected = signal.nlargest(top_n, "alpha_rank").copy()
    selected["target_weight"] = 1.0 / top_n
    selected = selected[
        [
            "date",
            "ticker",
            "predicted_residual_return",
            "alpha_rank",
            "risk_composite",
            "target_weight",
        ]
    ].sort_values("alpha_rank", ascending=False)

    output_dir = PROJECT_ROOT / "reports" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_dir / "v04_latest_candidate_portfolio.csv", index=False)
    manifest = {
        "specification": "v0.4 prospective ridge top-50 candidate",
        "signal_date": str(signal_date.date()),
        "training_last_signal_date": str(train["date"].max().date()),
        "market_data_last_date": str(price.index.max().date()),
        "holdings": len(selected),
        "prospective_eligible": bool(signal_date > FREEZE_DATE),
        "status": (
            "prospective record"
            if signal_date > FREEZE_DATE
            else "pre-freeze shadow output; excluded from prospective evidence"
        ),
    }
    (output_dir / "v04_latest_candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
