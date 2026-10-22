from __future__ import annotations

import numpy as np
import pandas as pd

FACTOR_COLUMNS = ["MKT_RF", "SMB", "HML", "RMW", "CMA", "MOM"]


def factor_regression(
    portfolio: pd.DataFrame,
    factors: pd.DataFrame,
    *,
    hac_lags: int = 5,
    subtract_risk_free_rate: bool = True,
) -> dict[str, float | int]:
    merged = portfolio[["date", "net_return"]].merge(factors, on="date", how="inner")
    required = ["net_return", "RF", *FACTOR_COLUMNS]
    merged = merged.dropna(subset=required).copy()
    if len(merged) <= len(FACTOR_COLUMNS) + 2:
        raise ValueError("Not enough overlapping observations for factor attribution")
    y = merged["net_return"].to_numpy()
    if subtract_risk_free_rate:
        y = y - merged["RF"].to_numpy()
    x = np.column_stack([np.ones(len(merged)), merged[FACTOR_COLUMNS].to_numpy()])
    inverse = np.linalg.pinv(x.T @ x)
    coefficients = inverse @ x.T @ y
    residuals = y - x @ coefficients

    meat = np.zeros((x.shape[1], x.shape[1]))
    score = x * residuals[:, None]
    meat += score.T @ score
    for lag in range(1, min(hac_lags, len(merged) - 1) + 1):
        weight = 1.0 - lag / (hac_lags + 1.0)
        covariance = score[lag:].T @ score[:-lag]
        meat += weight * (covariance + covariance.T)
    covariance_matrix = inverse @ meat @ inverse
    standard_errors = np.sqrt(np.diag(covariance_matrix))
    centered = y - y.mean()
    r_squared = 1.0 - float((residuals**2).sum() / (centered**2).sum())
    result: dict[str, float | int] = {
        "observations": len(merged),
        "annualized_alpha": float(coefficients[0] * 252.0),
        "alpha_t_stat_hac": float(coefficients[0] / standard_errors[0]),
        "r_squared": r_squared,
    }
    for name, coefficient in zip(FACTOR_COLUMNS, coefficients[1:], strict=True):
        result[f"beta_{name.lower()}"] = float(coefficient)
    return result
