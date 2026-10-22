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

- [ ] Reproduce the fixed drawdown-risk model.
- [ ] Add an expected-return momentum baseline.
- [ ] Combine expected return and drawdown risk using validation data only.
- [ ] Run expanding-window and regime-specific tests.
- [ ] Evaluate independent drawdown events and warning lead time.
- [ ] Run the frozen 2020–2026 modern holdout once.

Exit condition: results are reported against baselines with uncertainty estimates and no undisclosed tuning on the holdout.

## Phase 5: portfolio simulation

- [ ] Implement weekly and monthly rebalancing.
- [ ] Add sector, beta, turnover, and position constraints.
- [ ] Apply transaction-cost assumptions.
- [ ] Compare ordinary momentum, risk-filtered momentum, and risk-adjusted momentum.
- [ ] Report factor exposure, capacity limitations, and crisis-period behavior.

Exit condition: the portfolio claim matches the evidence; a negative result remains publishable.

## Phase 6: portfolio publication

- [ ] Add diagrams and selected charts.
- [ ] Include a small redistribution-safe example dataset.
- [ ] Add continuous integration and reproducibility instructions.
- [ ] Finalize the README research story and resume bullets.
- [ ] Review repository size, secrets, licenses, and data rights.

