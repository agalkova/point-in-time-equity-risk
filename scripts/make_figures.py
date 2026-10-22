from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports" / "tables"
FIGURES = PROJECT_ROOT / "docs" / "figures"
COLORS = {"navy": "#19324d", "blue": "#2f6f9f", "teal": "#2a9d8f", "gold": "#e9c46a"}


def finish(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def decile_figure() -> None:
    frame = pd.read_csv(TABLES / "modern_model_deciles.csv")
    plt.figure(figsize=(8.5, 4.8))
    plt.bar(frame["risk_decile"], frame["event_rate"] * 100.0, color=COLORS["blue"])
    plt.xlabel("Predicted risk decile (10 = highest risk)")
    plt.ylabel("40-day drawdown event rate (%)")
    plt.title("Modern holdout: realized drawdown risk rises monotonically")
    plt.xticks(frame["risk_decile"])
    plt.grid(axis="y", alpha=0.2)
    finish(FIGURES / "modern_decile_event_rates.png")


def annual_figure() -> None:
    frame = pd.read_csv(TABLES / "modern_model_annual.csv")
    _, axis = plt.subplots(figsize=(8.5, 4.8))
    axis.plot(
        frame["year"], frame["mean_daily_rank_ic"], marker="o", color=COLORS["navy"],
        label="Mean daily rank IC",
    )
    axis.plot(
        frame["year"], frame["top_minus_bottom_event_rate"], marker="o",
        color=COLORS["teal"], label="Top-minus-bottom event rate",
    )
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set_ylabel("Value")
    axis.set_title("Risk separation remained positive in every holdout year")
    axis.legend(frameon=False)
    axis.grid(alpha=0.2)
    finish(FIGURES / "modern_annual_stability.png")


def baseline_figure() -> None:
    summary = json.loads((TABLES / "modern_replication_summary.json").read_text())
    scores = summary["scores"]
    order = [
        "return_60", "volatility_20", "beta_60",
        "idiosyncratic_volatility_60", "fixed_rank_composite", "model",
    ]
    labels = ["60d return", "20d vol", "60d beta", "Idio vol", "Fixed composite", "Logistic"]
    average_precision = [scores[name]["average_precision"] for name in order]
    roc_auc = [scores[name]["roc_auc"] for name in order]
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    axes[0].barh(labels, average_precision, color=COLORS["blue"])
    axes[0].axvline(scores["model"]["prevalence"], color=COLORS["gold"], linestyle="--")
    axes[0].set_title("Average precision")
    axes[1].barh(labels, roc_auc, color=COLORS["teal"])
    axes[1].axvline(0.5, color=COLORS["gold"], linestyle="--")
    axes[1].set_title("ROC AUC")
    figure.suptitle("Model performance versus frozen single-factor baselines")
    for axis in axes:
        axis.grid(axis="x", alpha=0.2)
    finish(FIGURES / "modern_baseline_comparison.png")


def portfolio_figure() -> None:
    files = {
        "SPY buy-and-hold": "portfolio_monthly_spy_buy_hold_daily.csv",
        "Momentum": "portfolio_monthly_momentum_daily.csv",
        "Momentum excluding highest-risk quintile": "portfolio_monthly_risk_filtered_daily.csv",
    }
    plt.figure(figsize=(9.5, 5.2))
    for label, filename in files.items():
        frame = pd.read_csv(TABLES / filename, parse_dates=["date"])
        wealth = (1.0 + frame["net_return"]).cumprod()
        plt.plot(frame["date"], wealth, label=label)
    plt.ylabel("Growth of $1 after modeled costs")
    plt.title("Portfolio experiment: risk control is not an alpha claim")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)
    finish(FIGURES / "monthly_portfolio_wealth.png")


def advanced_model_figure() -> None:
    summary = json.loads((TABLES / "v02_walk_forward_summary.json").read_text())
    scores = summary["pooled_scores"]
    order = ["logistic", "hist_gradient_boosting", "ensemble", "fixed_composite"]
    labels = ["Logistic", "Gradient boosting", "50/50 ensemble", "Fixed composite"]
    metrics = [
        ("average_precision", "Average precision"),
        ("roc_auc", "ROC AUC"),
        ("mean_daily_rank_ic", "Mean daily rank IC"),
    ]
    figure, axes = plt.subplots(1, 3, figsize=(12, 4.6))
    for axis, (column, title) in zip(axes, metrics, strict=True):
        axis.barh(labels, [scores[name][column] for name in order], color=COLORS["blue"])
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.2)
    figure.suptitle("Exploratory walk-forward comparison: complexity offers a modest gain")
    finish(FIGURES / "v02_model_comparison.png")


def walk_forward_figure() -> None:
    frame = pd.read_csv(TABLES / "v02_walk_forward_folds.csv")
    labels = {
        "logistic": "Logistic",
        "hist_gradient_boosting": "Gradient boosting",
        "ensemble": "Ensemble",
        "fixed_composite": "Fixed composite",
    }
    plt.figure(figsize=(9.2, 5.0))
    for name, group in frame.groupby("model"):
        plt.plot(group["test_year"], group["average_precision"], marker="o", label=labels[name])
    plt.ylabel("Average precision")
    plt.title("Year-by-year walk-forward performance varies by market regime")
    plt.legend(frameon=False, ncol=2)
    plt.grid(alpha=0.2)
    finish(FIGURES / "v02_walk_forward_average_precision.png")


def importance_figure() -> None:
    frame = pd.read_csv(TABLES / "v02_boosting_permutation_importance.csv").head(12)
    frame = frame.sort_values("mean_average_precision_decrease")
    labels = frame["feature"].str.removeprefix("rank_").str.replace("_", " ")
    plt.figure(figsize=(9.2, 5.6))
    plt.barh(labels, frame["mean_average_precision_decrease"], color=COLORS["teal"])
    plt.xlabel("Decrease in average precision when shuffled")
    plt.title("Nonlinear model: leading out-of-sample feature importance")
    plt.grid(axis="x", alpha=0.2)
    finish(FIGURES / "v02_feature_importance.png")


def exposure_matched_figure() -> None:
    files = {
        "Risk-filtered momentum": "v02_exposure_matched_risk_filtered_daily.csv",
        "Ordinary momentum, same cash exposure": (
            "v02_exposure_matched_cash_matched_momentum_daily.csv"
        ),
    }
    plt.figure(figsize=(9.2, 5.0))
    for label, filename in files.items():
        frame = pd.read_csv(TABLES / filename, parse_dates=["date"])
        wealth = (1.0 + frame["net_return"]).cumprod()
        plt.plot(frame["date"], wealth, label=label)
    plt.ylabel("Growth of $1 after modeled costs")
    plt.title("Cash-matched diagnostic: filtering did not improve the portfolio")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)
    finish(FIGURES / "v02_exposure_matched_wealth.png")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    decile_figure()
    annual_figure()
    baseline_figure()
    portfolio_figure()
    advanced_model_figure()
    walk_forward_figure()
    importance_figure()
    exposure_matched_figure()
    print(f"Saved figures to {FIGURES}")


if __name__ == "__main__":
    main()
