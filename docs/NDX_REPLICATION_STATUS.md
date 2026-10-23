# Nasdaq-100 replication status

## 2026-10-22 — completed available-history run

The v0.7 cross-universe specification and reproducible pipeline were frozen before model
evaluation. The unchanged legacy-selected logistic model was then evaluated on every usable
Nasdaq-100 observation returned by the provider.

## Data outcome

- PtData returned all 88 requested monthly responses, but 49 responses from June 2019 through
  June 2023 contained empty constituent lists.
- The usable point-in-time membership history contains 39 month-end snapshots from July 2023
  through September 2026, 123 unique tickers, and 83,496 daily membership rows.
- Alpaca returned 217,527 adjusted SIP daily bars for all 123 requested tickers; no symbol was
  missing.
- Feature lookback and complete-target requirements make the actual evaluation window
  2023-10-24 through 2026-08-04.

The provider limitation means the pre-specified 2020–2026 annual-stability rule cannot be
evaluated. The report records overall `passed` as null rather than treating unavailable years as
a model failure.

## Available-history results

- 9,242 eligible stock-date observations and 1,918 severe-drawdown events.
- ROC AUC: **0.663**.
- Average precision: **0.326**, or **1.57×** the 0.208 event prevalence.
- Mean daily rank IC: **0.226**, with 40-day block interval **[0.147, 0.287]**.
- Highest-risk-decile event rate: **40.69%** versus **9.48%** in the lowest decile, a
  **4.29×** risk ratio.
- Annual rank IC was positive in all four observed calendar years (partial 2023 and 2026).
- Average daily NDX/S&P 500 membership overlap was **85.0%**, so this is not a fully independent
  security-universe test.

These results pass all three evaluable frozen thresholds and are supportive evidence that the
drawdown-risk ranking transfers to a growth/technology-heavy universe. They do not satisfy the
original seven-year confirmation requirement because the free membership history is unavailable.

## Reproduction

```bash
.venv/bin/python scripts/download_ndx_membership.py
.venv/bin/python scripts/download_ndx_alpaca.py
.venv/bin/python scripts/run_ndx_replication.py
```
