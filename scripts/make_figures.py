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


def alpha_wealth_figure() -> None:
    files = {
        "Ridge top 50 (post-spec candidate)": "v03_ridge_long_only_post_spec_daily.csv",
        "Risk-adjusted ensemble": "v03_risk_adjusted_long_only_daily.csv",
        "Equal-weight universe": "v03_equal_weight_universe_daily.csv",
        "SPY": "v03_spy_buy_hold_daily.csv",
    }
    plt.figure(figsize=(9.5, 5.2))
    for label, filename in files.items():
        frame = pd.read_csv(TABLES / filename, parse_dates=["date"])
        wealth = (1.0 + frame["net_return"]).cumprod()
        plt.plot(frame["date"], wealth, label=label)
    plt.ylabel("Growth of $1 after modeled costs")
    plt.title("Exploratory alpha study: the linear-model candidate is promising, not proven")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)
    finish(FIGURES / "v03_alpha_candidate_wealth.png")


def alpha_walk_forward_figure() -> None:
    frame = pd.read_csv(TABLES / "v03_alpha_walk_forward_folds.csv")
    names = {
        "ridge": "Ridge",
        "hist_gradient_boosting": "Gradient boosting",
        "ensemble": "Ensemble",
        "fixed_momentum": "Fixed momentum",
        "risk_adjusted": "Risk-adjusted ensemble",
    }
    plt.figure(figsize=(9.5, 5.2))
    for name, group in frame.groupby("model"):
        plt.plot(
            group["test_year"],
            group["mean_monthly_rank_ic"],
            marker="o",
            label=names[name],
        )
    plt.axhline(0.0, color="black", linewidth=0.8)
    plt.ylabel("Mean monthly cross-sectional rank IC")
    plt.title("Expected-return ranking is unstable across years")
    plt.legend(frameon=False, ncol=2)
    plt.grid(alpha=0.2)
    finish(FIGURES / "v03_alpha_walk_forward_ic.png")


def alpha_sensitivity_figure() -> None:
    frame = pd.read_csv(TABLES / "v03_ridge_portfolio_sensitivity.csv")
    frame = frame[frame["mode"].eq("long_only")]
    plt.figure(figsize=(8.8, 5.0))
    for positions, group in frame.groupby("positions_per_side"):
        plt.plot(
            group["one_way_cost_bps"],
            group["annualized_alpha"] * 100.0,
            marker="o",
            label=f"Top {positions}",
        )
    plt.axhline(0.0, color="black", linewidth=0.8)
    plt.xlabel("One-way transaction cost (basis points)")
    plt.ylabel("Estimated annual six-factor alpha (%)")
    plt.title("Post-spec sensitivity: positive estimate, limited statistical confidence")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)
    finish(FIGURES / "v03_ridge_alpha_sensitivity.png")


def fundamental_pilot_figure() -> None:
    folds = pd.read_csv(TABLES / "v05_fundamental_walk_forward_folds.csv")
    names = {
        "price_only": "Price only",
        "fundamentals_only": "Fundamentals only",
        "combined": "Combined",
    }
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for name, group in folds.groupby("model"):
        axes[0].plot(
            group["test_year"],
            group["mean_monthly_rank_ic"],
            marker="o",
            label=names[name],
        )
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].set_ylabel("Mean monthly rank IC")
    axes[0].set_title("Small predictive lift is not stable")
    axes[0].legend(frameon=False)
    axes[0].grid(alpha=0.2)

    for name, label in names.items():
        frame = pd.read_csv(
            TABLES / f"v05_fundamental_{name}_daily.csv", parse_dates=["date"]
        )
        axes[1].plot(
            frame["date"],
            (1.0 + frame["net_return"]).cumprod(),
            label=label,
        )
    axes[1].set_ylabel("Growth of $1 after modeled costs")
    axes[1].set_title("Combined pilot did not improve the portfolio")
    axes[1].legend(frameon=False)
    axes[1].grid(alpha=0.2)
    figure.suptitle("v0.5 point-in-time fundamentals pilot")
    finish(FIGURES / "v05_fundamental_pilot.png")


def optimized_portfolio_figure() -> None:
    files = {
        "Ridge top 50": "v03_ridge_long_only_post_spec_daily.csv",
        "Constrained optimizer": "v06_optimized_ridge_daily.csv",
    }
    plt.figure(figsize=(9.4, 5.0))
    for label, filename in files.items():
        frame = pd.read_csv(TABLES / filename, parse_dates=["date"])
        plt.plot(
            frame["date"],
            (1.0 + frame["net_return"]).cumprod(),
            label=label,
        )
    plt.ylabel("Growth of $1 after modeled costs")
    plt.title("Portfolio engineering did not improve the ridge candidate")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)
    finish(FIGURES / "v06_portfolio_engineering.png")


def ndx_transfer_figure() -> None:
    annual = pd.read_csv(TABLES / "v07_ndx_annual.csv")
    summary = json.loads((TABLES / "v07_ndx_summary.json").read_text())
    primary = summary["primary_ndx_results"]
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.8))
    axes[0].plot(
        annual["year"],
        annual["mean_daily_rank_ic"],
        marker="o",
        linewidth=2,
        color=COLORS["navy"],
    )
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].set_xticks(annual["year"])
    axes[0].set_ylabel("Mean daily rank IC")
    axes[0].set_title("Positive ranking in every observed year")
    axes[0].grid(alpha=0.2)

    labels = ["Lowest-risk decile", "Highest-risk decile"]
    rates = [
        primary["bottom_decile_event_rate"] * 100.0,
        primary["top_decile_event_rate"] * 100.0,
    ]
    axes[1].bar(labels, rates, color=[COLORS["teal"], COLORS["blue"]])
    axes[1].set_ylabel("40-day drawdown event rate (%)")
    axes[1].set_title(f"{primary['top_to_bottom_risk_ratio']:.2f}× risk separation")
    axes[1].grid(axis="y", alpha=0.2)
    figure.suptitle("Unchanged-model Nasdaq-100 transfer test (2020–2026)")
    finish(FIGURES / "v07_ndx_transfer.png")


def cross_universe_figure() -> None:
    modern = json.loads((TABLES / "modern_replication_summary.json").read_text())["scores"][
        "model"
    ]
    ndx = json.loads((TABLES / "v07_ndx_summary.json").read_text())["primary_ndx_results"]
    sp400 = json.loads((TABLES / "v08_sp400_summary.json").read_text())[
        "primary_sp400_results"
    ]
    labels = ["S&P 500", "Nasdaq-100", "S&P 400"]
    results = [modern, ndx, sp400]
    metrics = [
        ("roc_auc", "ROC AUC", 0.5),
        ("average_precision_lift", "Average-precision lift", 1.0),
        ("mean_daily_rank_ic", "Mean daily rank IC", 0.0),
        ("top_to_bottom_risk_ratio", "Highest/lowest risk ratio", 1.0),
    ]
    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.4))
    colors = [COLORS["navy"], COLORS["blue"], COLORS["teal"]]
    for axis, (metric, title, reference) in zip(axes.flat, metrics, strict=True):
        values = [result[metric] for result in results]
        axis.bar(labels, values, color=colors)
        axis.axhline(reference, color=COLORS["gold"], linestyle="--", linewidth=1.2)
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.2)
        for index, value in enumerate(values):
            axis.text(index, value, f"{value:.2f}", ha="center", va="bottom")
    figure.suptitle("Unchanged drawdown-risk model transfers across three universes")
    finish(FIGURES / "v08_cross_universe_validation.png")


def fundamental_data_quality_figure() -> None:
    summary = json.loads((TABLES / "v14_fundamental_ablation_summary.json").read_text())
    audit = summary["panel_audit"]
    labels = ["Issuer identity", "Fresh filing", "Quality score"]
    values = [
        audit["identity_coverage"] * 100.0,
        audit["filing_coverage_after_550_day_expiry"] * 100.0,
        audit["quality_score_coverage"] * 100.0,
    ]
    colors = [COLORS["navy"], COLORS["blue"], COLORS["teal"]]
    figure, axis = plt.subplots(figsize=(8.8, 4.8))
    bars = axis.bar(labels, values, color=colors, width=0.62)
    axis.set_ylim(0.0, 105.0)
    axis.set_ylabel("Eligible stock-month observations covered (%)")
    axis.set_title("Point-in-time SEC panel: broad coverage with no future-filing joins")
    axis.grid(axis="y", alpha=0.2)
    for bar, value in zip(bars, values, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 1.2,
            f"{value:.1f}%",
            ha="center",
            va="bottom",
        )
    figure.text(
        0.5,
        0.01,
        (
            f"{audit['panel_rows']:,} stock-month rows • {audit['issuers']:,} issuers • "
            f"{audit['timing_violations']} future-filing violations"
        ),
        ha="center",
        color=COLORS["navy"],
    )
    finish(FIGURES / "v14_fundamental_data_quality.png")


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
    alpha_wealth_figure()
    alpha_walk_forward_figure()
    alpha_sensitivity_figure()
    fundamental_pilot_figure()
    optimized_portfolio_figure()
    ndx_transfer_figure()
    cross_universe_figure()
    fundamental_data_quality_figure()
    print(f"Saved figures to {FIGURES}")


if __name__ == "__main__":
    main()
