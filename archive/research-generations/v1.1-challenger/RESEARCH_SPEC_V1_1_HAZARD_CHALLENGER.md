# Research specification v1.1 — modern hazard challenger

## Status and purpose

Frozen before generating v1.1 challenger results. All modern periods have already been inspected in
earlier project stages, so this is an exploratory model-release study rather than a new untouched
confirmatory test.

The active v0.9 hazard model was trained on legacy 2012–2019 episodes. Its current S&P 500 input
data are complete and fresh, but its 40-day score distribution has moved beyond the fixed operating
limit. Version 1.1 asks whether a model trained only on point-in-time modern data can preserve the
validated ranking signal while restoring an acceptable operating distribution.

## Frozen candidates

Keep the v0.9 episode definition, 31 feature columns, four discrete-time intervals, regularization,
and prediction code unchanged. Compare exactly two challenger fits:

1. `modern_expanding`: S&P 500 episodes from 2020-01-01 through 2024-12-31.
2. `modern_rolling`: S&P 500 episodes from 2022-01-01 through 2024-12-31.

No feature selection, hyperparameter search, nonlinear model, or probability recalibration is
allowed in this version. Both candidates use `C=0.01`, seed 42, and the existing pooled logistic
hazard implementation.

## Selection and evaluation

- Select one challenger using only 2025 S&P 500 episodes with complete 60-trading-day outcomes.
- Primary selection metric: 40-day average-precision lift. Tie-breaker: 40-day ROC AUC.
- After selection, evaluate the chosen model once on mature 2026 S&P 500 outcomes.
- Apply the unchanged selected model to mature 2026 Nasdaq-100 and S&P 400 episodes as transfer
  diagnostics.
- Compare every evaluation row with the active legacy champion on the exact same episodes.
- Measure current score PSI against the fixed 2024–2025 operating reference using all available
  episode onsets, including unlabeled recent onsets.

## Promotion rule

The challenger remains shadow-only unless all S&P 500 requirements pass:

- ROC AUC at least 0.60 and no more than 0.01 below the champion;
- average-precision lift at least 1.25 and at least 0.05 above the champion;
- Brier score no more than 0.01 worse than the champion;
- current score PSI no greater than 0.25;
- at least one of the two transfer universes independently satisfies the same discrimination and
  precision-lift floors without applying the improvement requirement.

Passing permits a separate reviewed registration and promotion decision; it does not automatically
replace the active model. Failure is retained and reported without changing thresholds or selecting
a third candidate.
