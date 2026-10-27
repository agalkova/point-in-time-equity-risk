# Project plan

## Objective

Produce a public, reproducible portfolio project that demonstrates quantitative research, financial-data engineering, and careful backtesting.

## Phase 1: foundation and legacy reproduction

- [x] Preserve the original project as read-only source material.
- [x] Complete a leakage-aware feasibility test.
- [x] Establish a separate project folder.
- [x] Freeze the initial research specification.
- [x] Add project configuration, decision log, and progress log.
- [x] Reproduce the feasibility result from the modular package.
- [x] Add automated timing and data-contract tests.

Exit condition: the modular pipeline reproduces the recorded legacy metrics within documented tolerances.

## Phase 2: market-data pipeline

- [x] Implement an authenticated Alpaca historical-bars client.
- [x] Create a 20-security pilot universe covering ordinary, renamed, acquired, and delisted cases.
- [x] Download raw and adjusted SIP daily bars for the pilot.
- [x] Store request manifests and immutable raw responses.
- [x] Reconcile 2016–2019 prices and volumes against the legacy source.
- [x] Produce missing-symbol and corporate-action reports.

Exit condition: price and volume definitions are understood, ticker mappings are documented, and the overlap audit passes.

## Phase 3: point-in-time research dataset

- [x] Build a dated ticker-history alias table with explicit reuse handling.
- [x] Add point-in-time S&P 500 membership.
- [ ] Add sector classifications available on each signal date.
- [x] Build leakage-safe price/volume features with explicit signal-date timing.
- [x] Add data-quality checks for duplicates, membership coverage, ticker reuse, and missing symbols.

Exit condition: every model row is reproducible from timestamped source records without future information.

## Phase 4: models and validation

- [x] Reproduce the fixed drawdown-risk model.
- [x] Add an expected-return momentum baseline.
- [x] Combine expected return and drawdown risk using validation data only.
- [x] Run calendar-year and regime-sensitive stability tests.
- [x] Evaluate independent drawdown events and warning lead time.
- [x] Run the frozen 2020–2026 modern holdout once.

Exit condition: results are reported against baselines with uncertainty estimates and no undisclosed tuning on the holdout.

## Phase 5: portfolio simulation

- [x] Implement weekly and monthly rebalancing.
- [x] Add beta measurement, turnover reporting, and position constraints.
- [x] Apply transaction-cost assumptions.
- [x] Compare ordinary momentum, risk-filtered momentum, and risk-adjusted momentum.
- [x] Report market exposure, capacity limitations, and crisis-period behavior.

Exit condition: the portfolio claim matches the evidence; a negative result remains publishable.

## Phase 6: portfolio publication

- [x] Add diagrams and selected charts.
- [x] Include a small redistribution-safe synthetic example dataset.
- [x] Add continuous integration and reproducibility instructions.
- [x] Finalize the README research story and resume bullets.
- [x] Review repository size, secrets, licenses, and data rights.

## Phase 7: advanced exploratory research

- [x] Freeze a separately labeled v0.2 exploratory specification.
- [x] Add downside, tail, liquidity, path, and market-state features.
- [x] Run purged expanding yearly walk-forward validation.
- [x] Compare linear, nonlinear, ensemble, and transparent composite scores.
- [x] Add calibration, permutation importance, independent-event, and lead-time diagnostics.
- [x] Test the portfolio conclusion after matching daily cash exposure.
- [x] Document the negative portfolio result without converting risk prediction into an alpha claim.

Exit condition: the advanced layer is reproducible, clearly separated from the frozen v0.1
claim, and supports only conclusions justified by the evidence.

## Phase 8: expected-return and alpha research

- [x] Freeze a distinct beta-adjusted future-return target and full-universe protocol.
- [x] Add residual-momentum, reversal, liquidity, and market-state predictors.
- [x] Produce six expanding yearly walk-forward prediction sets.
- [x] Compare linear, nonlinear, ensemble, and transparent momentum scores.
- [x] Add long-only, long-short, equal-weight, and SPY portfolio comparisons.
- [x] Download free official factor data and estimate six-factor alpha with HAC errors.
- [x] Stress-test the ridge candidate across position counts and transaction costs.
- [x] Freeze a prospective candidate without promoting the post-spec result to proven alpha.
- [x] Begin recording month-end prospective signals after the freeze date.

Exit condition: a complete alpha-research attempt is published honestly, and any stronger
claim depends on observations that were not available when the candidate was frozen.

## Phase 9: SEC fundamentals and issuer identity

- [x] Process all official quarterly Financial Statement Data Set archives from 2014 Q1 through
  2026 Q3.
- [x] Resolve point-in-time ticker intervals to permanent SEC CIK identifiers.
- [x] Freeze separate nonfinancial, Financials, and Real Estate accounting schemas.
- [x] Join statements on public filing date and expire stale annual filings.
- [x] Run matched price-only, fundamentals-only, and combined walk-forward comparisons.
- [x] Report the failed stability and long-short alpha tests without post-result retuning.

Exit condition: the accounting panel passes identity, freshness, and timing gates, and the model
claim remains limited to the evidence.

## Phase 10: public release

- [x] Consolidate the README around the primary results and limitations.
- [x] Add a deterministic synthetic end-to-end demonstration.
- [x] Add one-command verification and a public-repository audit.
- [x] Expand CI to cover the SEC point-in-time path and release checks.
- [x] Preregister the independent S&P 400 fundamental transfer test.
- [ ] Reprocess SEC archives for the S&P 400 issuer set and run the frozen transfer test.

The final item requires a new SEC archive pass. It is deliberately separate from the completed
public release and must not be represented as an existing result.

