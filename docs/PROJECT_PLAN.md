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
- [ ] Add an expected-return momentum baseline.
- [x] Combine expected return and drawdown risk using validation data only.
- [x] Run calendar-year and regime-sensitive stability tests.
- [ ] Evaluate independent drawdown events and warning lead time.
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

