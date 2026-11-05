# Research specification v0.2

Status: exploratory extension
Parent: frozen v0.1
Created: 2026-10-22

## Why this version exists

Version 0.1 established that the signal replicates as a cross-sectional drawdown-risk
ranker. Its modern holdout has now been opened and can never be described as untouched
again. Version 0.2 may use those observations for retrospective model comparison, but it
must be labeled exploratory. A genuinely new confirmation period begins only with data
that was unavailable after this specification was written.

## Added research questions

1. Does performance survive expanding yearly walk-forward tests with a 40-trading-day
   purge between training labels and each test interval?
2. Do nonlinear interactions improve on regularized logistic regression and a fixed factor
   composite?
3. Are predicted probabilities calibrated, not merely well ranked?
4. Does the result survive deterministic thinning into non-overlapping signal events?
5. Can a risk overlay improve a portfolio after matching gross exposure and reporting
   volatility, rather than benefiting mechanically from holding more cash?

## Additional features

Only information observable at the signal close is permitted:

- downside semivolatility over 20 and 60 trading days;
- return skewness and kurtosis;
- trailing maximum drawdown over 60 and 120 days;
- 60-day lower-tail return quantile;
- 20-day return autocorrelation;
- price-volume correlation;
- Amihud-style illiquidity based on trailing absolute return divided by dollar volume.

All security-level features enter models as same-day cross-sectional percentile ranks.

## Models fixed before execution

- Regularized logistic regression with `C=0.01`.
- Histogram gradient boosting with the parameters in `configs/research_v0_2.toml`.
- A 50/50 probability ensemble of those two models.

No parameter is selected on a test year. Each model is refit using only observations that
would have been available before that test interval.

## Walk-forward protocol

For each calendar year from 2020 through 2026:

1. Train on all earlier legacy and modern observations.
2. Remove the final 40 distinct trading dates from training so their outcome windows cannot
   overlap the test interval.
3. Fit each fixed model once.
4. Score the year without model selection on that year.

The pooled out-of-fold predictions are evaluated with average precision, ROC AUC, Brier
score, calibration error, daily rank IC, decile separation, and annual stability.

## Event evaluation

Overlapping eligible signals are deterministically thinned per security. After retaining a
signal, the next 40 trading dates for that security are skipped. A warning is the top 20%
of same-day out-of-fold risk scores. Report event recall, precision, false-warning rate, and
lead time to the first 15% threshold breach.

## Portfolio extension

Any v0.2 portfolio comparison must report both raw and exposure-matched results. It must
include turnover, costs, invested weight, and realized volatility. An improvement caused
only by additional cash is not evidence of security-selection skill.

## Claim policy

Version 0.2 can improve engineering and provide stronger retrospective evidence. It cannot
restore an untouched 2020–2026 holdout. Confirmation of changes motivated by existing
results requires future data or an independent market/universe.
