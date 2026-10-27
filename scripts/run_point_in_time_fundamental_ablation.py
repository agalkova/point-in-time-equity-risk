from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from build_point_in_time_fundamental_panel import (
    AUDIT_PATH,
    PANEL_PATH,
    build_panel,
    load_config_v14,
)
from run_alpha_research import annual_returns, load_modern_panel
from sklearn.base import clone

from risk_managed_momentum.config import load_config
from risk_managed_momentum.data.factors import load_french_factors
from risk_managed_momentum.evaluation.alpha import alpha_score_summary, monthly_rank_ic
from risk_managed_momentum.evaluation.alpha_portfolio import simulate_alpha_portfolio
from risk_managed_momentum.evaluation.attribution import factor_regression
from risk_managed_momentum.evaluation.portfolio import performance_summary
from risk_managed_momentum.evaluation.ranking import moving_block_interval
from risk_managed_momentum.evaluation.walk_forward import expanding_year_folds
from risk_managed_momentum.features.sec_fundamentals import FUNDAMENTAL_FEATURES
from risk_managed_momentum.models.alpha import alpha_model_factories

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES = PROJECT_ROOT / "reports/tables"


def add_rank(frame: pd.DataFrame, source: str, destination: str) -> None:
    frame[destination] = frame.groupby("date")[source].rank(method="average", pct=True)


def pooled_summary(frame: pd.DataFrame, score: str, config: dict) -> dict:
    values = alpha_score_summary(frame, score)
    rank_ic = monthly_rank_ic(frame, score)
    lower, upper = moving_block_interval(
        rank_ic,
        block_length=int(config["inference"]["block_length_months"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )
    return {**values, "rank_ic_block_interval": [lower, upper]}


def main() -> None:
    config = load_config_v14()
    base = load_config(PROJECT_ROOT / "configs/research.toml")
    if PANEL_PATH.exists() and AUDIT_PATH.exists():
        panel = pd.read_csv(PANEL_PATH, parse_dates=["date", "filed", "period"])
        audit = json.loads(AUDIT_PATH.read_text())
    else:
        panel, audit = build_panel()
    if not audit["panel_gate_passed"]:
        raise RuntimeError("Point-in-time panel gates failed; the model remains disabled")

    frame = panel.dropna(subset=["future_residual_return_21"]).copy()
    price_features = list(alpha_config_feature_columns(frame))
    rank_features = [f"fundamental_rank_{feature}" for feature in FUNDAMENTAL_FEATURES]
    availability_features = [f"available_{feature}" for feature in FUNDAMENTAL_FEATURES]
    fundamental_features = [
        *rank_features,
        *availability_features,
        "fundamental_quality_score",
        "fundamental_feature_count",
        "fundamental_schema_financials",
        "fundamental_schema_real_estate",
        "filing_age_years",
    ]
    feature_sets = {
        "price": price_features,
        "fundamental": fundamental_features,
        "combined": [*price_features, *fundamental_features],
    }

    validation = config["validation"]
    folds = expanding_year_folds(
        frame["date"],
        first_test_year=int(validation["first_test_year"]),
        last_test_year=int(validation["last_test_year"]),
        purge_trading_days=int(validation["purge_month_end_signals"]),
    )
    factories = alpha_model_factories(config)
    outputs: list[pd.DataFrame] = []
    fold_rows: list[dict] = []
    for fold in folds:
        train = frame[frame["date"].isin(fold.train_dates)].copy()
        test = frame[frame["date"].isin(fold.test_dates)].copy()
        if len(train) < int(validation["minimum_training_observations"]) or test.empty:
            continue
        for feature_set, columns in feature_sets.items():
            for model_name, prototype in factories.items():
                prediction = f"prediction_{feature_set}_{model_name}"
                score = f"score_{feature_set}_{model_name}"
                model = clone(prototype).fit(train[columns], train["future_residual_return_21"])
                test[prediction] = model.predict(test[columns])
                add_rank(test, prediction, score)
            test[f"score_{feature_set}_ensemble"] = (
                float(config["ensemble"]["ridge_weight"])
                * test[f"score_{feature_set}_ridge"]
                + float(config["ensemble"]["hist_gradient_boosting_weight"])
                * test[f"score_{feature_set}_hist_gradient_boosting"]
            )
            for model_name in ["ridge", "hist_gradient_boosting", "ensemble"]:
                fold_rows.append(
                    {
                        "test_year": fold.test_year,
                        "feature_set": feature_set,
                        "model": model_name,
                        **alpha_score_summary(test, f"score_{feature_set}_{model_name}"),
                    }
                )
        outputs.append(test)
    if not outputs:
        raise RuntimeError("No walk-forward folds met the frozen training requirement")
    oof = pd.concat(outputs, ignore_index=True).sort_values(["date", "ticker"])

    pooled = {
        f"{feature_set}_{model_name}": pooled_summary(
            oof, f"score_{feature_set}_{model_name}", config
        )
        for feature_set in feature_sets
        for model_name in ["ridge", "hist_gradient_boosting", "ensemble"]
    }
    price_ic = monthly_rank_ic(oof, "score_price_ensemble")
    combined_ic = monthly_rank_ic(oof, "score_combined_ensemble")
    paired_delta = combined_ic.sub(price_ic).dropna()
    delta_lower, delta_upper = moving_block_interval(
        paired_delta,
        block_length=int(config["inference"]["block_length_months"]),
        iterations=int(config["inference"]["bootstrap_iterations"]),
        random_seed=int(config["project"]["random_seed"]),
    )
    by_year = {
        str(year): float(values.mean())
        for year, values in paired_delta.groupby(paired_delta.index.year)
    }
    by_schema = {}
    for schema, group in oof.dropna(subset=["fundamental_schema"]).groupby(
        "fundamental_schema"
    ):
        base_ic = monthly_rank_ic(group, "score_price_ensemble")
        enhanced_ic = monthly_rank_ic(group, "score_combined_ensemble")
        common = enhanced_ic.sub(base_ic).dropna()
        by_schema[str(schema)] = {
            "months": len(common),
            "price_rank_ic": float(base_ic.mean()),
            "combined_rank_ic": float(enhanced_ic.mean()),
            "combined_minus_price_rank_ic": float(common.mean()),
        }

    complete = oof[oof["fundamental_quality_score"].notna()].copy()
    complete_case = {
        "observations": len(complete),
        "price": pooled_summary(complete, "score_price_ensemble", config),
        "combined": pooled_summary(complete, "score_combined_ensemble", config),
    }

    price, _, _ = load_modern_panel(base)
    # The research period is frozen through 2026-09-30. Later operational bars can include
    # unresolved corporate actions and are outside this ablation's target window.
    portfolio_end = pd.Timestamp(base["splits"]["modern_holdout"]["end"])
    price = price.loc[:portfolio_end]
    benchmark_bars = pd.read_csv(base["modern_source"]["benchmark_path"])
    benchmark_bars["date"] = pd.to_datetime(benchmark_bars["date"]).dt.normalize()
    benchmark_returns = (
        benchmark_bars.sort_values("date").set_index("date")["close"].pct_change(fill_method=None)
    )
    factor_path = PROJECT_ROOT / "data/raw/fama_french/daily_six_factors.csv.gz"
    factors = load_french_factors(str(factor_path)) if factor_path.exists() else None
    portfolios = {}
    portfolio_specs = [
        ("price_long_only", "price", "long_only"),
        ("fundamental_long_only", "fundamental", "long_only"),
        ("combined_long_only", "combined", "long_only"),
        # Long-short mappings are reported only as post-specification diagnostics. They do not
        # change the frozen primary long-only comparison or its pass/fail decision.
        ("price_long_short_post_spec", "price", "long_short"),
        ("fundamental_long_short_post_spec", "fundamental", "long_short"),
        ("combined_long_short_post_spec", "combined", "long_short"),
    ]
    for portfolio_name, feature_set, mode in portfolio_specs:
        daily = simulate_alpha_portfolio(
            price,
            oof,
            score_column=f"score_{feature_set}_ensemble",
            mode=mode,
            top_n=int(config["portfolio"]["top_n"]),
            one_way_cost_bps=float(config["portfolio"]["one_way_cost_bps"]),
        )
        result = {
            **performance_summary(daily, benchmark_returns=benchmark_returns),
            "annual_returns": annual_returns(daily),
        }
        if factors is not None:
            result["factor_attribution"] = factor_regression(
                daily, factors, subtract_risk_free_rate=mode != "long_short"
            )
        portfolios[portfolio_name] = result
        daily.to_csv(TABLES / f"v14_{portfolio_name}_daily.csv", index=False)

    delta_mean = float(paired_delta.mean())
    positive_years = sum(value > 0.0 for value in by_year.values())
    positive_schemas = sum(
        values["combined_minus_price_rank_ic"] > 0.0 for values in by_schema.values()
    )
    summary = {
        "specification_version": config["project"]["specification_version"],
        "claim_status": config["project"]["claim_status"],
        "panel_audit": audit,
        "out_of_fold_observations": len(oof),
        "out_of_fold_months": int(oof["date"].nunique()),
        "test_years": sorted(oof["date"].dt.year.unique().astype(int).tolist()),
        "feature_counts": {name: len(columns) for name, columns in feature_sets.items()},
        "pooled_predictive_results": pooled,
        "combined_minus_price_rank_ic": {
            "mean_monthly_delta": delta_mean,
            "block_interval": [delta_lower, delta_upper],
            "by_year": by_year,
            "positive_years": positive_years,
            "years": len(by_year),
            "by_accounting_schema": by_schema,
            "positive_accounting_schemas": positive_schemas,
            "accounting_schemas": len(by_schema),
        },
        "complete_case_sensitivity": complete_case,
        "portfolio_results": portfolios,
        "post_specification_portfolio_diagnostics": [
            "price_long_short_post_spec",
            "fundamental_long_short_post_spec",
            "combined_long_short_post_spec",
        ],
        "fundamental_increment_passes_frozen_directional_gate": (
            delta_mean > 0.0
            and positive_years > len(by_year) / 2.0
            and positive_schemas > len(by_schema) / 2.0
        ),
        "independent_confirmation_required": True,
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(TABLES / "v14_fundamental_walk_forward_folds.csv", index=False)
    keep = [
        "date",
        "ticker",
        "cik",
        "filed",
        "fundamental_schema",
        "future_return_21",
        "future_residual_return_21",
        *[
            f"score_{feature_set}_{model_name}"
            for feature_set in feature_sets
            for model_name in ["ridge", "hist_gradient_boosting", "ensemble"]
        ],
    ]
    oof[keep].to_csv(
        TABLES / "v14_fundamental_oof_predictions.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    (TABLES / "v14_fundamental_ablation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


def alpha_config_feature_columns(frame: pd.DataFrame) -> list[str]:
    """Recover the frozen price-feature columns without rebuilding the price panel."""
    regime = [
        "market_return_1m",
        "market_return_3m",
        "market_volatility_20",
        "market_breadth_1m",
        "cross_sectional_dispersion_1m",
    ]
    ranked = sorted(column for column in frame if column.startswith("rank_"))
    columns = [*ranked, *regime]
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ValueError(f"Panel is missing frozen price features: {missing}")
    return columns


if __name__ == "__main__":
    main()
