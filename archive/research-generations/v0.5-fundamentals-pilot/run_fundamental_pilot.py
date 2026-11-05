from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pandas as pd
from run_alpha_research import annual_returns, load_alpha_config, load_modern_panel
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.factors import load_french_factors
from risk_managed_momentum.evaluation.alpha import alpha_score_summary, monthly_rank_ic
from risk_managed_momentum.evaluation.alpha_portfolio import simulate_alpha_portfolio
from risk_managed_momentum.evaluation.attribution import factor_regression
from risk_managed_momentum.evaluation.portfolio import performance_summary
from risk_managed_momentum.evaluation.ranking import moving_block_interval
from risk_managed_momentum.evaluation.walk_forward import expanding_year_folds
from risk_managed_momentum.features.alpha import build_alpha_dataset
from risk_managed_momentum.features.fundamentals import (
    FUNDAMENTAL_FEATURES,
    add_cross_sectional_fundamental_ranks,
    build_filing_features,
    point_in_time_fundamentals,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def load_pilot_config() -> dict:
    with (PROJECT_ROOT / "configs/research_v0_5_fundamentals.toml").open("rb") as handle:
        return tomllib.load(handle)


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=alpha)),
        ]
    )


def add_rank(frame: pd.DataFrame, source: str, destination: str) -> None:
    frame[destination] = frame.groupby("date")[source].rank(method="average", pct=True)


def score_summary(frame: pd.DataFrame, score_column: str, config: dict) -> dict:
    metrics = alpha_score_summary(frame, score_column)
    rank_ic = monthly_rank_ic(frame, score_column)
    lower, upper = moving_block_interval(
        rank_ic,
        block_length=int(config["inference"]["block_length_months"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )
    return {**metrics, "rank_ic_block_interval": [lower, upper]}


def main() -> None:
    base_config = load_config(PROJECT_ROOT / "configs/research.toml")
    alpha_config = load_alpha_config()
    config = load_pilot_config()
    facts_path = PROJECT_ROOT / "data/interim/sec/annual_companyfacts.csv.gz"
    if not facts_path.exists():
        raise SystemExit(
            "Missing SEC pilot data. Run scripts/download_sec_fundamentals.py first."
        )

    price, volume, membership = load_modern_panel(base_config)
    alpha = build_alpha_dataset(price, volume, base_config, alpha_config, membership)
    annual = pd.read_csv(facts_path, parse_dates=["end", "filed"])
    filing_features = build_filing_features(annual)
    pilot_tickers = sorted(annual["ticker"].unique())
    frame = alpha.frame[alpha.frame["ticker"].isin(pilot_tickers)].copy()
    fundamentals = point_in_time_fundamentals(filing_features, frame[["date", "ticker"]])
    frame = frame.merge(
        fundamentals,
        on=["date", "ticker"],
        how="left",
        validate="one_to_one",
    )
    frame["fundamental_coverage"] = frame[FUNDAMENTAL_FEATURES].notna().sum(axis=1)
    frame = frame[
        frame["fundamental_coverage"].ge(
            int(config["pilot"]["minimum_fundamental_features"])
        )
    ].copy()
    frame, fundamental_rank_columns = add_cross_sectional_fundamental_ranks(frame)

    validation = config["validation"]
    folds = expanding_year_folds(
        frame["date"],
        first_test_year=int(validation["first_test_year"]),
        last_test_year=int(validation["last_test_year"]),
        purge_trading_days=int(validation["purge_month_end_signals"]),
    )
    feature_sets = {
        "price_only": alpha.feature_columns,
        "fundamentals_only": fundamental_rank_columns,
        "combined": [*alpha.feature_columns, *fundamental_rank_columns],
    }
    prototype = ridge_pipeline(float(config["model"]["ridge_alpha"]))
    outputs = []
    fold_rows = []
    for fold in folds:
        train = frame[frame["date"].isin(fold.train_dates)].copy()
        test = frame[frame["date"].isin(fold.test_dates)].copy()
        if len(train) < int(validation["minimum_training_observations"]) or test.empty:
            continue
        for name, columns in feature_sets.items():
            model = clone(prototype).fit(train[columns], train["future_residual_return_21"])
            test[f"prediction_{name}"] = model.predict(test[columns])
            add_rank(test, f"prediction_{name}", f"score_{name}")
            fold_rows.append(
                {
                    "test_year": fold.test_year,
                    "model": name,
                    **alpha_score_summary(test, f"score_{name}"),
                }
            )
        outputs.append(test)
    if not outputs:
        raise RuntimeError("No walk-forward folds met the pilot training requirement")
    oof = pd.concat(outputs, ignore_index=True).sort_values(["date", "ticker"])

    pooled = {name: score_summary(oof, f"score_{name}", config) for name in feature_sets}
    price_ic = monthly_rank_ic(oof, "score_price_only")
    combined_ic = monthly_rank_ic(oof, "score_combined")
    paired_ic_delta = combined_ic.sub(price_ic).dropna()
    delta_lower, delta_upper = moving_block_interval(
        paired_ic_delta,
        block_length=int(config["inference"]["block_length_months"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )
    factor_path = PROJECT_ROOT / "data/raw/fama_french/daily_six_factors.csv.gz"
    factors = load_french_factors(str(factor_path)) if factor_path.exists() else None
    portfolios = {}
    for name in feature_sets:
        daily = simulate_alpha_portfolio(
            price,
            oof,
            score_column=f"score_{name}",
            mode="long_only",
            top_n=int(config["portfolio"]["top_n"]),
            one_way_cost_bps=float(config["portfolio"]["one_way_cost_bps"]),
        )
        result = {**performance_summary(daily), "annual_returns": annual_returns(daily)}
        if factors is not None:
            result["factor_attribution"] = factor_regression(daily, factors)
        portfolios[name] = result
        daily.to_csv(TABLES / f"v05_fundamental_{name}_daily.csv", index=False)

    coverage = {
        column: float(oof[column].notna().mean()) for column in FUNDAMENTAL_FEATURES
    }
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": (
            "engineering and signal-value pilot only; current-survivor sample cannot support "
            "an investment claim"
        ),
        "pilot_tickers": pilot_tickers,
        "observations": len(oof),
        "months": int(oof["date"].nunique()),
        "test_years": sorted(oof["date"].dt.year.unique().astype(int).tolist()),
        "fundamental_feature_coverage": coverage,
        "pooled_predictive_results": pooled,
        "combined_minus_price_rank_ic": {
            "mean_monthly_delta": float(paired_ic_delta.mean()),
            "block_interval": [delta_lower, delta_upper],
            "positive_years": int(
                paired_ic_delta.groupby(paired_ic_delta.index.year).mean().gt(0.0).sum()
            ),
            "years": int(paired_ic_delta.index.year.nunique()),
        },
        "portfolio_results": portfolios,
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(
        TABLES / "v05_fundamental_walk_forward_folds.csv", index=False
    )
    oof[
        [
            "date",
            "ticker",
            "filed",
            "end",
            "future_return_21",
            "future_residual_return_21",
            *[f"score_{name}" for name in feature_sets],
        ]
    ].to_csv(
        TABLES / "v05_fundamental_oof_predictions.csv.gz",
        index=False,
        compression="gzip",
    )
    (TABLES / "v05_fundamental_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
