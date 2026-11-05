# Research specification v0.9 — exuberance episode hazard

## Research question

When a stock first enters an unusually strong, near-peak run-up, can only information available on that date estimate the probability and timing of a subsequent 15% drawdown?

This is the corrected form of the original “detecting bubbles” project. The original buildup intuition is retained, but a bubble is not assigned backward after a later crash. The observable state is called **exuberance**; the forward outcome is called **drawdown hazard**.

## Frozen design

This specification was written before v0.9 results were generated. The historical evaluation periods have already been opened in earlier project versions, so all v0.9 findings are exploratory rather than a new confirmatory test.

### Stage 1 — exuberance episode onset

A stock enters an exuberance episode when all of the following are true on date `t`:

- its trailing 60-trading-day return is at least 20%;
- it is no more than 10% below its trailing 60-day high;
- it is a point-in-time member of the evaluated universe; and
- it has not met the same eligibility rule during the prior 20 trading days.

Only the first qualifying date is modeled. This prevents long runs from being counted as dozens of nearly identical examples and makes the unit of analysis an investable warning decision.

### Stage 2 — forward drawdown hazard

The event is the first future close at least 15% below the signal-date close. The model estimates discrete conditional hazards over four fixed intervals:

1. trading days 1–10;
2. trading days 11–20;
3. trading days 21–40; and
4. trading days 41–60.

The cumulative probability by each horizon is derived from the interval hazards, so the estimated 10-, 20-, 40-, and 60-day risks are guaranteed to be monotonic.

### Features and model

The predictor set is frozen to the 31 point-in-time price, volume, market-regime, tail-risk, and liquidity features introduced in v0.2. These include corrected versions of the original notebook’s ideas: run-up strength, trend acceleration, proximity to highs, volatility, volume abnormality, and price-volume behavior.

The model is one pooled L2-regularized logistic discrete-time hazard model. Interval indicators estimate the baseline hazard; feature coefficients are shared across horizons. Regularization is fixed at `C = 0.01`, inherited from the legacy validation choice. No v0.9 hyperparameter search is permitted.

### Training and evaluation

- Training: original legacy S&P 500-style panel, 2012-12-01 through 2019-03-15.
- Evaluation: 2020-01-01 through 2026-09-30.
- Evaluation universes: point-in-time S&P 500, Nasdaq-100, and S&P 400 panels already assembled in the repository.
- A full 60-trading-day forward window is required for every episode.

### Primary outputs

- episode count and event prevalence by universe;
- ROC AUC, average precision and lift, and Brier score at 10, 20, 40, and 60 days;
- top-versus-bottom risk-quintile event rates;
- median warning lead time among correctly high-risk events;
- calibration by risk quintile;
- standardized logistic coefficients for interpretation;
- comparison with trailing 60-day return as a simple benchmark.

## Interpretation boundaries

The model does not prove that a security is fundamentally overvalued, identify a classical economic bubble, or establish a profitable trading strategy. A strong result would support a narrower and defensible claim: conditional on a measurable exuberant price state, public market data contains transferable information about the timing of severe near-term drawdown risk.

