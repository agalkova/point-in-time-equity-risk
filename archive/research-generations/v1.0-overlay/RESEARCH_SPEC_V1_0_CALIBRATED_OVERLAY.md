# Research specification v1.0 — walk-forward calibration and episode overlay

## Purpose

Version 0.9 produced a transferable ranking of drawdown risk but underpredicted modern event prevalence. Version 1.0 asks two narrower questions without changing or retuning the ranking model:

1. Can an intercept-only rule, estimated solely from already matured prior outcomes, improve the honesty of the multi-horizon probabilities?
2. Does excluding the frozen highest-risk episode group improve the realized economics of an otherwise identical post-exuberance momentum cohort?

This specification was committed after v0.9 results were known but before v1.0 results were generated. All findings are exploratory.

## Frozen walk-forward recalibration

- Keep the v0.9 features, coefficients, regularization, episode definition, and interval hazards unchanged.
- For each universe and test year from 2021 through 2026, use only earlier episodes from the same universe whose complete 60-trading-day outcomes would have matured at least 92 calendar days before January 1 of the test year.
- Estimate one logit-intercept adjustment across all four interval-hazard rows while fixing the original model score coefficient at exactly one.
- Require at least 100 matured prior episodes; otherwise apply zero adjustment.
- Apply that single adjustment to all interval hazards in the test year and rebuild monotonic cumulative 10-, 20-, 40-, and 60-day probabilities.
- Evaluate raw and calibrated scores on the identical 2021–2026 rows using Brier score, log loss, mean predicted risk versus prevalence, and ranking metrics.

The adjustment may change probability levels but cannot change within-year rankings.

## Frozen episode portfolio diagnostic

- Score legacy training episodes with the unchanged v0.9 model.
- Define “high risk” once as a raw 40-day risk at or above the 80th percentile of legacy training scores.
- For each modern universe, form a baseline portfolio containing every new exuberance episode and an overlay portfolio that excludes only episodes above that frozen threshold.
- Enter at the close one trading day after the signal and hold for 40 trading days.
- Equal-weight all active cohorts each day. Reweight retained overlay positions to the same unit gross exposure whenever at least one retained position is active; otherwise hold cash.
- Apply 10 basis points of one-way turnover costs to both portfolios.
- Report annualized return, volatility, zero-rate Sharpe ratio, maximum drawdown, average daily turnover, invested-day rate, high-risk exclusion rate, and overlay-minus-baseline differences.

The portfolio is a diagnostic of warning utility. It is not a preregistered alpha strategy and will not be promoted based on the outcome.

## Decision rule

Recalibration is useful only if it lowers pooled Brier score and log loss at the 40-day horizon in at least two of the three universes without altering ROC AUC beyond numerical tolerance.

The overlay is economically useful only if it improves net Sharpe ratio and maximum drawdown in at least two universes. Return improvement is reported but is not required for a risk overlay.

