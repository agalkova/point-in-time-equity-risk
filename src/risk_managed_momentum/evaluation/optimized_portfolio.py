from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass(frozen=True)
class OptimizedWeights:
    weights: pd.Series
    estimated_beta: float
    estimated_volatility: float
    objective_value: float
    solver_iterations: int


def _risk_estimates(
    asset_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
    *,
    shrinkage: float,
) -> tuple[np.ndarray, np.ndarray]:
    aligned = asset_returns.join(benchmark_returns.rename("benchmark"), how="inner")
    assets = aligned[asset_returns.columns]
    benchmark = aligned["benchmark"]
    # Pairwise covariance is stabilized by replacing missing observations with each asset's
    # trailing mean (normally close to zero), then applying fixed diagonal shrinkage.
    filled = assets.fillna(assets.mean()).fillna(0.0)
    sample = filled.cov().to_numpy(dtype=float) * 252.0
    diagonal = np.diag(np.diag(sample))
    covariance = (1.0 - shrinkage) * sample + shrinkage * diagonal
    benchmark_variance = float(benchmark.var(ddof=1))
    beta = np.array(
        [
            float(assets[column].cov(benchmark) / benchmark_variance)
            if benchmark_variance > 0.0
            else np.nan
            for column in assets
        ]
    )
    return covariance, beta


def optimize_alpha_weights(
    signals: pd.DataFrame,
    trailing_returns: pd.DataFrame,
    trailing_benchmark_returns: pd.Series,
    previous_weights: pd.Series,
    config: dict[str, Any],
    *,
    score_column: str = "score_ridge",
) -> OptimizedWeights:
    settings = config["optimizer"]
    candidates = signals.dropna(subset=["ticker", score_column]).nlargest(
        int(settings["candidate_count"]), score_column
    )
    coverage = trailing_returns.notna().sum()
    tickers = [
        ticker
        for ticker in candidates["ticker"].astype(str)
        if ticker in coverage.index
        and coverage[ticker] >= int(settings["minimum_asset_observations"])
    ]
    if len(tickers) * float(settings["maximum_position_weight"]) < 1.0:
        raise RuntimeError("Too few risk-estimable candidates for the position cap")
    candidates = candidates.set_index("ticker").loc[tickers]
    history = trailing_returns[tickers]
    covariance, beta = _risk_estimates(
        history,
        trailing_benchmark_returns,
        shrinkage=float(settings["covariance_diagonal_shrinkage"]),
    )
    valid = np.isfinite(beta) & np.isfinite(np.diag(covariance))
    tickers = list(np.asarray(tickers)[valid])
    candidates = candidates.loc[tickers]
    covariance = covariance[np.ix_(valid, valid)]
    beta = beta[valid]
    if len(tickers) * float(settings["maximum_position_weight"]) < 1.0:
        raise RuntimeError("Too few finite risk estimates for the position cap")

    score = candidates[score_column].rank(method="average", pct=True).to_numpy(dtype=float)
    score = score - float(score.mean())
    prior = previous_weights.reindex(tickers, fill_value=0.0).to_numpy(dtype=float)
    maximum_weight = float(settings["maximum_position_weight"])
    risk_aversion = float(settings["risk_aversion"])
    turnover_penalty = float(settings["turnover_penalty"])

    def objective(weights: np.ndarray) -> float:
        expected_score = float(score @ weights)
        variance = float(weights @ covariance @ weights)
        smooth_turnover = float(np.sqrt((weights - prior) ** 2 + 1e-10).sum())
        return -expected_score + risk_aversion * variance + turnover_penalty * smooth_turnover

    constraints = [
        {"type": "eq", "fun": lambda weights: float(weights.sum() - 1.0)},
        {
            "type": "ineq",
            "fun": lambda weights: float(
                beta @ weights - float(settings["minimum_beta"])
            ),
        },
        {
            "type": "ineq",
            "fun": lambda weights: float(
                float(settings["maximum_beta"]) - beta @ weights
            ),
        },
    ]
    initial = np.full(len(tickers), 1.0 / len(tickers))
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=[(0.0, maximum_weight)] * len(tickers),
        constraints=constraints,
        options={"maxiter": int(settings["solver_max_iterations"]), "ftol": 1e-10},
    )
    if not result.success:
        raise RuntimeError(f"Portfolio optimization failed: {result.message}")
    weights = pd.Series(result.x, index=tickers).clip(lower=0.0)
    weights = weights.div(weights.sum())
    estimated_variance = float(weights.to_numpy() @ covariance @ weights.to_numpy())
    return OptimizedWeights(
        weights=weights[weights > 1e-8].sort_values(ascending=False),
        estimated_beta=float(beta @ weights.to_numpy()),
        estimated_volatility=float(np.sqrt(max(estimated_variance, 0.0))),
        objective_value=float(result.fun),
        solver_iterations=int(result.nit),
    )


def simulate_optimized_alpha_portfolio(
    price: pd.DataFrame,
    benchmark_returns: pd.Series,
    signals: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    price = price.sort_index().astype(float)
    returns = price.pct_change(fill_method=None)
    work = signals.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.normalize()
    work = work[work["date"].isin(price.index)]
    by_date = {date: group for date, group in work.groupby("date")}
    if not by_date:
        raise ValueError("No signal dates overlap the price panel")

    current = pd.Series(0.0, index=price.columns)
    cost_rate = float(config["portfolio"]["one_way_cost_bps"]) / 10_000.0
    lookback = int(config["optimizer"]["covariance_lookback_days"])
    rows = []
    holdings = []
    simulation_dates = price.index[price.index >= min(by_date)]
    for date in simulation_dates:
        asset_return = returns.loc[date]
        missing_exposure = float(current[asset_return.isna()].abs().sum())
        gross_return = float((current * asset_return.fillna(0.0)).sum())
        if 1.0 + gross_return > 0.0:
            current = current.mul(1.0 + asset_return.fillna(0.0)).div(1.0 + gross_return)

        traded_notional = 0.0
        diagnostics: OptimizedWeights | None = None
        if date in by_date:
            location = price.index.get_loc(date)
            start = max(0, location - lookback + 1)
            history_dates = price.index[start : location + 1]
            diagnostics = optimize_alpha_weights(
                by_date[date],
                returns.loc[history_dates],
                benchmark_returns.reindex(history_dates),
                current,
                config,
            )
            target = diagnostics.weights.reindex(price.columns, fill_value=0.0)
            traded_notional = float(target.sub(current).abs().sum())
            current = target
            for ticker, weight in diagnostics.weights.items():
                holdings.append(
                    {
                        "date": date,
                        "ticker": ticker,
                        "target_weight": weight,
                        "estimated_beta": diagnostics.estimated_beta,
                        "estimated_volatility": diagnostics.estimated_volatility,
                    }
                )
        transaction_cost = traded_notional * cost_rate
        rows.append(
            {
                "date": date,
                "net_return": gross_return - transaction_cost,
                "gross_return": gross_return,
                "traded_notional": traded_notional,
                "transaction_cost": transaction_cost,
                "net_exposure": float(current.sum()),
                "gross_exposure": float(current.abs().sum()),
                "invested_weight": float(current.abs().sum()),
                "positions": int((current.abs() > 1e-8).sum()),
                "missing_exposure": missing_exposure,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(holdings)
