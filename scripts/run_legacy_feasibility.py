from __future__ import annotations

import json
from pathlib import Path

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.evaluation.ranking import (
    classification_metrics,
    daily_rank_ic,
    decile_table,
    moving_block_interval,
)
from risk_managed_momentum.features.build import build_research_dataset, split_research_dataset
from risk_managed_momentum.models.drawdown import select_logistic_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = load_config(PROJECT_ROOT / "configs" / "research.toml")
    price, volume = load_legacy_wide(
        config["legacy_source"]["price_path"],
        config["legacy_source"]["volume_path"],
    )
    dataset = build_research_dataset(price, volume, config)
    splits = split_research_dataset(dataset, config)
    selected = select_logistic_model(
        splits["train"],
        splits["validation"],
        dataset.feature_columns,
        random_seed=int(config["project"]["random_seed"]),
    )
    test = splits["legacy_test"].copy()
    test["risk_score"] = selected.model.predict_proba(test[dataset.feature_columns])[:, 1]
    metrics = classification_metrics(test["target"], test["risk_score"].to_numpy())
    deciles = decile_table(test, "risk_score")
    rank_ic = daily_rank_ic(test, "risk_score")
    interval = moving_block_interval(
        rank_ic,
        block_length=int(config["inference"]["block_bootstrap_days"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )

    summary = {
        "specification_version": config["project"]["specification_version"],
        "selected_model": selected.name,
        "split_observations": {name: int(len(frame)) for name, frame in splits.items()},
        "test_metrics": metrics,
        "mean_daily_rank_ic": float(rank_ic.mean()),
        "mean_daily_rank_ic_95pct_block_interval": list(interval),
        "top_decile_event_rate": float(deciles.loc[deciles["risk_decile"] == 10, "event_rate"].iloc[0]),
        "bottom_decile_event_rate": float(deciles.loc[deciles["risk_decile"] == 1, "event_rate"].iloc[0]),
    }
    summary["top_to_bottom_risk_ratio"] = (
        summary["top_decile_event_rate"] / summary["bottom_decile_event_rate"]
    )

    output_dir = PROJECT_ROOT / "reports" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    selected.selection_table.to_csv(output_dir / "legacy_model_selection.csv", index=False)
    deciles.to_csv(output_dir / "legacy_test_deciles.csv", index=False)
    rank_ic.rename_axis("date").reset_index().to_csv(
        output_dir / "legacy_daily_rank_ic.csv", index=False
    )
    (output_dir / "legacy_feasibility_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

