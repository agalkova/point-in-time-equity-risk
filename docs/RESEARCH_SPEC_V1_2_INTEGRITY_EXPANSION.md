# Research specification v1.2 — integrity repair and historical expansion

## Status

Frozen after diagnosing index-exit censoring and measuring source coverage, but before fitting or
evaluating any v1.2 model. The 2020–2026 periods have been inspected in earlier versions, so all
historical model comparisons remain exploratory. No historical result can become a new untouched
confirmation.

## Data repair

1. Extend adjusted and raw Alpaca SIP bars and reconstructed S&P 500 membership to 2016-01-01.
2. Keep membership as an eligibility mask; do not truncate a security's price history when it
   leaves the index.
3. Fill at most three internal missing trading days, and only when trading subsequently resumes.
4. Resolve terminal mergers from Alpaca corporate actions. Use explicit, primary-source-backed
   overrides where the provider's symbol-keyed response omits an old or reused ticker.
5. Value cash mergers at contractual cash consideration, stock mergers through the successor, and
   a documented worthless removal at zero. Unknown terminal paths remain missing and fail closed.
6. Portfolio simulation must reject a missing held-security return rather than substituting zero.

The audit must report every repaired and unresolved episode. These rules are not model parameters
and cannot be altered based on whether predictive metrics improve.

## Market-only robustness study

Keep the v0.9 episode definition, 31 features, four hazard intervals, `C=0.01`, and pooled logistic
implementation. Fit exactly three candidates through 2024:

- `expanded_2016`: corrected episodes beginning 2016-07-01;
- `modern_2020`: corrected episodes beginning 2020-01-01;
- `rolling_2022`: corrected episodes beginning 2022-01-01.

Choose one on 2025 S&P 500 40-day average-precision lift, breaking a tie with ROC AUC. Report 2026
S&P 500 performance without calling it confirmatory. Report paired 60-trading-day block-bootstrap
intervals for challenger-minus-champion metric differences. Do not promote a model from this
exploratory repair study automatically.

## Fundamental ablation

The market-only model remains primary. A separate ablation may add exactly six filing-date-available
annual features: gross margin, operating margin, operating-cash-flow margin, return on assets,
liabilities/assets, and asset growth. The ablation is worthwhile only if point-in-time coverage is
audited across historical members. Missing fundamentals must not be converted into a
current-survivor universe.

## Prospective confirmation

Beginning 2026-10-27, retain every frozen-model prediction before its outcome. Do not tune the
model during the record. Review only after both 12 calendar months and 250 mature episodes are
available. This prospective record—not another reuse of 2020–2026—is the next confirmatory test.
