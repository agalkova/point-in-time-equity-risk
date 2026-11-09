# v0.6 ridge portfolio-engineering specification

Status: frozen before execution  
Created: 2026-10-22

## Purpose

Test whether a pre-specified constrained optimizer improves the implementation quality of the
existing ridge alpha candidate. The alpha scores, target, features, and walk-forward predictions
remain unchanged. This experiment changes portfolio construction only.

## Inputs

- Frozen v0.3 ridge out-of-fold monthly scores
- Adjusted daily prices available on each rebalance date
- SPY daily returns available on each rebalance date
- No fundamental-pilot output
- No current sector classification in the historical optimizer

Current sectors are intentionally excluded because the project lacks a licensed historical
classification series. Backfilling today's sectors would weaken the point-in-time design.

## Optimizer

- Long-only and fully invested
- Candidate set: 100 highest ridge-ranked eligible stocks
- Maximum position weight: 3%
- Covariance and beta lookback: 126 trading days
- Minimum return observations per asset: 80
- Covariance estimator: 50% sample covariance plus 50% diagonal covariance
- Portfolio beta constraint: 0.75–1.05 versus SPY
- Objective: maximize cross-sectional ridge rank minus 3.0 times annualized variance minus
  0.03 times smooth one-way turnover
- SLSQP maximum iterations: 500
- One-way trading cost: 10 basis points

Every risk estimate uses observations on or before the rebalance date. Failure to solve a month
raises an error rather than silently changing the strategy.

## Benchmark and pass rule

The matched benchmark is the frozen equal-weight ridge top-50 candidate at the same 10-basis-point
cost. SPY and six-factor attribution remain contextual comparisons.

The optimizer passes only if it improves maximum drawdown and Sharpe ratio without reducing
annualized return by more than two percentage points, and its factor-alpha estimate remains
positive. Statistical uncertainty and year-by-year stability must be reported regardless.

This remains historical exploratory evidence. It cannot replace the v0.4 prospective record.
