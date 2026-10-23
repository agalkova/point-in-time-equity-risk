from __future__ import annotations

import json
import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import roc_auc_score

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.legacy import load_legacy_wide
from risk_managed_momentum.evaluation.episode_portfolio import (
    episode_overlay_returns,
    portfolio_summary,
)
from risk_managed_momentum.evaluation.recalibration import (
    probability_summary,
    walk_forward_intercept_recalibration,
)
from risk_managed_momentum.features.episodes import build_exuberance_episode_dataset
from risk_managed_momentum.models.hazard import fit_hazard_model, predict_cumulative_risk
from run_exuberance_hazard import load_modern_sp500, load_ndx, load_sp400

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"
FIGURES = PROJECT_ROOT / "docs/figures"


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def make_figure(
    calibration_metrics: pd.DataFrame,
    portfolio_series: dict[str, pd.DataFrame],
) -> None:
    colors = {"S&P 500": "#205493", "Nasdaq-100": "#2ca25f", "S&P 400": "#d95f0e"}
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    horizon = calibration_metrics[calibration_metrics["horizon_days"].eq(40)]
    universes = list(colors)
    x = range(len(universes))
    raw = [
        float(horizon[(horizon["universe"].eq(name)) & horizon["score_type"].eq("raw")]["brier_score"].iloc[0])
        for name in universes
    ]
    calibrated = [
        float(horizon[(horizon["universe"].eq(name)) & horizon["score_type"].eq("calibrated")]["brier_score"].iloc[0])
        for name in universes
    ]
    axes[0].bar([value - 0.18 for value in x], raw, width=0.36, label="Raw")
    axes[0].bar([value + 0.18 for value in x], calibrated, width=0.36, label="Walk-forward calibrated")
    axes[0].set_xticks(list(x), universes)
    axes[0].set_ylabel("Brier score (lower is better)")
    axes[0].set_title("40-day probability accuracy")
    axes[0].legend(frameon=False)

    for universe, frame in portfolio_series.items():
        baseline = (1.0 + frame["baseline_net_return"]).cumprod()
        overlay = (1.0 + frame["overlay_net_return"]).cumprod()
        axes[1].plot(baseline.index, baseline, color=colors[universe], alpha=0.45, linewidth=1.5)
        axes[1].plot(
            overlay.index,
            overlay,
            color=colors[universe],
            linewidth=2,
            label=f"{universe} overlay",
        )
    axes[1].set_title("Net wealth of episode cohorts")
    axes[1].set_ylabel("Growth of $1")
    axes[1].legend(frameon=False)
    figure.suptitle("Walk-forward calibration and frozen risk overlay", fontsize=14, fontweight="bold")
    figure.tight_layout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURES / "v10_calibrated_overlay.png", dpi=180, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    hazard_config = load_toml(PROJECT_ROOT / "configs/research_v0_9_exuberance_hazard.toml")
    config = load_toml(PROJECT_ROOT / "configs/research_v1_0_calibrated_overlay.toml")
    legacy_price, legacy_volume = load_legacy_wide(
        PROJECT_ROOT / base_config["legacy_source"]["price_path"],
        PROJECT_ROOT / base_config["legacy_source"]["volume_path"],
    )
    legacy = build_exuberance_episode_dataset(
        legacy_price, legacy_volume, base_config, hazard_config
    )
    training = legacy.frame[legacy.frame["date"].between(
        hazard_config["training"]["start"], hazard_config["training"]["end"]
    )].copy()
    model = fit_hazard_model(
        training,
        legacy.feature_columns,
        hazard_config["outcome"]["horizon_end_days"],
        c=float(hazard_config["model"]["c"]),
        maximum_iterations=int(hazard_config["model"]["maximum_iterations"]),
        random_seed=int(hazard_config["project"]["random_seed"]),
    )
    training_scored = predict_cumulative_risk(model, training)
    risk_horizon = int(config["portfolio"]["signal_horizon_days"])
    high_risk_threshold = float(
        training_scored[f"risk_{risk_horizon}"].quantile(
            float(config["portfolio"]["legacy_high_risk_quantile"])
        )
    )

    loaders = {
        "S&P 500": lambda: load_modern_sp500(base_config),
        "Nasdaq-100": load_ndx,
        "S&P 400": load_sp400,
    }
    calibration_rows = []
    audit_frames = []
    portfolio_rows = []
    portfolio_series = {}
    recalibration_passes = {}
    overlay_passes = {}
    for universe, loader in loaders.items():
        price, volume, membership = loader()
        episodes = build_exuberance_episode_dataset(
            price, volume, base_config, hazard_config, membership=membership
        )
        evaluation = episodes.frame[episodes.frame["date"].between(
            hazard_config["evaluation"]["start"], hazard_config["evaluation"]["end"]
        )].copy()
        raw_scored = predict_cumulative_risk(model, evaluation)
        calibrated, audit = walk_forward_intercept_recalibration(
            raw_scored,
            model.horizons,
            first_year=int(config["recalibration"]["first_evaluation_year"]),
            last_year=int(config["recalibration"]["last_evaluation_year"]),
            maturity_buffer_calendar_days=int(
                config["recalibration"]["outcome_maturity_buffer_calendar_days"]
            ),
            minimum_prior_episodes=int(config["recalibration"]["minimum_prior_episodes"]),
        )
        audit["universe"] = universe
        audit_frames.append(audit)
        for horizon in model.horizons:
            for score_type, score_column in {
                "raw": f"risk_{horizon}",
                "calibrated": f"calibrated_risk_{horizon}",
            }.items():
                calibration_rows.append(
                    {
                        "universe": universe,
                        "horizon_days": horizon,
                        "score_type": score_type,
                        **probability_summary(
                            calibrated,
                            target_column=f"target_{horizon}",
                            score_column=score_column,
                        ),
                    }
                )

        yearly_auc_difference = []
        for _, group in calibrated.groupby(calibrated["date"].dt.year):
            if group[f"target_{risk_horizon}"].nunique() < 2:
                continue
            raw_auc = roc_auc_score(group[f"target_{risk_horizon}"], group[f"risk_{risk_horizon}"])
            calibrated_auc = roc_auc_score(
                group[f"target_{risk_horizon}"], group[f"calibrated_risk_{risk_horizon}"]
            )
            yearly_auc_difference.append(abs(raw_auc - calibrated_auc))

        portfolio, diagnostics = episode_overlay_returns(
            price,
            raw_scored,
            risk_column=f"risk_{risk_horizon}",
            high_risk_threshold=high_risk_threshold,
            holding_period=int(config["portfolio"]["holding_period_trading_days"]),
            entry_delay=int(config["portfolio"]["entry_delay_trading_days"]),
            one_way_cost_bps=float(config["portfolio"]["one_way_cost_bps"]),
        )
        portfolio_series[universe] = portfolio
        baseline = portfolio_summary(
            portfolio["baseline_net_return"],
            portfolio["baseline_turnover"],
            int(config["portfolio"]["annualization_days"]),
        )
        overlay = portfolio_summary(
            portfolio["overlay_net_return"],
            portfolio["overlay_turnover"],
            int(config["portfolio"]["annualization_days"]),
        )
        for portfolio_name, values in {"baseline": baseline, "overlay": overlay}.items():
            portfolio_rows.append(
                {"universe": universe, "portfolio": portfolio_name, **diagnostics, **values}
            )
        horizon_metrics = pd.DataFrame(calibration_rows)
        current = horizon_metrics[
            horizon_metrics["universe"].eq(universe)
            & horizon_metrics["horizon_days"].eq(risk_horizon)
        ].set_index("score_type")
        recalibration_passes[universe] = {
            "brier_improved": bool(
                current.loc["calibrated", "brier_score"] < current.loc["raw", "brier_score"]
            ),
            "log_loss_improved": bool(
                current.loc["calibrated", "log_loss"] < current.loc["raw", "log_loss"]
            ),
            "maximum_within_year_auc_change": max(yearly_auc_difference, default=0.0),
        }
        overlay_passes[universe] = {
            "sharpe_improved": bool(overlay["sharpe_ratio"] > baseline["sharpe_ratio"]),
            "maximum_drawdown_improved": bool(
                overlay["maximum_drawdown"] > baseline["maximum_drawdown"]
            ),
            "annual_return_change": overlay["annual_return"] - baseline["annual_return"],
        }

    calibration_metrics = pd.DataFrame(calibration_rows)
    calibration_audit = pd.concat(audit_frames, ignore_index=True)
    portfolio_metrics = pd.DataFrame(portfolio_rows)
    recalibration_universes_passed = sum(
        value["brier_improved"] and value["log_loss_improved"]
        for value in recalibration_passes.values()
    )
    overlay_universes_passed = sum(
        value["sharpe_improved"] and value["maximum_drawdown_improved"]
        for value in overlay_passes.values()
    )
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": config["project"]["claim_status"],
        "frozen_legacy_80pct_risk_threshold": high_risk_threshold,
        "recalibration": {
            "universe_results": recalibration_passes,
            "universes_passing": recalibration_universes_passed,
            "decision_rule_passed": recalibration_universes_passed >= 2,
        },
        "portfolio_overlay": {
            "universe_results": overlay_passes,
            "universes_passing": overlay_universes_passed,
            "decision_rule_passed": overlay_universes_passed >= 2,
        },
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    calibration_metrics.to_csv(TABLES / "v10_calibration_metrics.csv", index=False)
    calibration_audit.to_csv(TABLES / "v10_calibration_audit.csv", index=False)
    portfolio_metrics.to_csv(TABLES / "v10_episode_overlay_metrics.csv", index=False)
    for universe, frame in portfolio_series.items():
        slug = universe.lower().replace("&", "sp").replace("-", "").replace(" ", "_")
        frame.to_csv(TABLES / f"v10_{slug}_portfolio_returns.csv.gz", compression="gzip")
    (TABLES / "v10_calibrated_overlay_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    make_figure(calibration_metrics, portfolio_series)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

