# Progress log

## 2026-10-21

Completed:

- Audited the original notebooks and datasets without modifying them.
- Replaced hindsight bubble membership with a forward 40-day drawdown target.
- Ran a chronological train, validation, and legacy-test feasibility study.
- Added factor comparisons, alternate target definitions, annual stability checks, and a 40-day moving-block bootstrap.
- Rejected an immediate alpha claim after a naïve daily exclusion portfolio failed.
- Created this separate project with a frozen specification and decision log.
- Added the first Alpaca historical SIP client and data-audit foundation.
- Reproduced the recorded feasibility metrics exactly from the modular package.
- Added 13 passing tests covering target timing, sample isolation, legacy data contracts, response normalization, reconciliation, and refusal of IEX data.
- Added raw-versus-adjusted overlap reconciliation for price levels, returns, consolidated volume, coverage dates, and ticker mappings.
- Downloaded raw and fully adjusted Alpaca SIP pilot data for 20 securities over 2016-01-01 through 2019-06-12.
- Reconciled 16,810 overlapping security-date records with no missing requested symbols, including renamed and delisted names.
- Confirmed that raw Alpaca closes are the closest level match to the legacy price field for all 20 pilot securities.
- Confirmed strong provider agreement: median raw-return correlation 0.9994, median adjusted-return correlation 1.0000, and median raw-volume correlation 0.9905.
- Added automatic loading of the private, Git-ignored project `.env` file for downloads.
- Reconstructed 2019–2026 point-in-time S&P 500 membership from 412 public constituent changes.
- Downloaded 1,101,390 adjusted Alpaca SIP bars for 642 returned symbols and a separate SPY benchmark.
- Added dated corporate-action chains and historical `asof` requests, including protection against an unrelated reuse of ticker `STI`.
- Opened the frozen modern holdout once: 91,299 observations, 0.671 ROC AUC, 1.73× average-precision lift, and 18.84 percentage points of top-minus-bottom decile separation.
- Confirmed positive risk separation in every modern calendar year.
- Completed weekly and monthly cost-aware portfolio tests. The return optimizer selected no risk penalty; the monthly exclusion overlay reduced risk but also return and exposure.
- Added 18 passing tests, CI, publication figures, a results report, and resume bullets.

## 2026-10-22

Completed:

- Froze an explicitly exploratory v0.2 specification while preserving v0.1 as the
  confirmatory result.
- Expanded the research panel to 31 price, volume, liquidity, tail-risk, path, and
  market-state features.
- Added seven expanding calendar-year folds with a 40-trading-day purge and 91,299
  out-of-fold modern predictions.
- Compared regularized logistic regression, histogram gradient boosting, a fixed 50/50
  ensemble, and a transparent four-factor composite.
- Added calibration error, yearly stability, permutation importance, non-overlapping
  event evaluation, warning precision/recall, and first-breach lead time.
- Added a cash-matched portfolio diagnostic using walk-forward risk scores. The filter did
  not improve return, Sharpe, or maximum drawdown versus ordinary momentum at the same
  realized daily exposure.
- Expanded the automated suite to 23 tests and added four publication figures.

Current interpretation:

- The advanced workflow strengthens the evidence for a cross-sectional drawdown-risk rank.
- The nonlinear model does not dominate; the ensemble is modestly stronger on probabilistic
  metrics, while the transparent composite remains competitive.
- The exposure-matched result rejects the stronger portfolio claim. This is not a hidden
  alpha strategy, and the repository should say so plainly.

Alpha research extension:

- Froze v0.3 before execution with a beta-adjusted 21-day return target, 22 fixed features,
  monthly signals, six yearly walk-forward folds, and 10 basis-point one-way costs.
- Added 33,598 out-of-fold security-month predictions across 68 month-end cross-sections.
- Rejected the primary ensemble alpha claim: 12.31% annual return, 0.68 Sharpe, and -1.12%
  estimated annual six-factor alpha versus 14.78% and 0.89 for SPY.
- Identified a post-spec ridge candidate with 21.34% annual return, 1.19 Sharpe, -18.83%
  maximum drawdown, and 5.48% estimated annual factor alpha; its 1.46 alpha t-statistic is
  insufficient for a confirmed claim.
- Confirmed that the ridge estimate remains economically positive across 25, 50, and 100
  positions and 5–20 basis-point transaction-cost assumptions, but no sensitivity reaches
  a 2.0 alpha t-statistic.
- Froze the ridge top-50 candidate for future month-end observation without retroactively
  promoting it to the primary specification.
- Expanded the automated suite to 26 passing tests.

Next actions:

1. Begin the v0.4 prospective record at the first month-end after the freeze date.
2. Optionally add licensed point-in-time sector data; do not infer historical sectors from current labels.
3. Create the GitHub remote only when authorized by the project owner.

