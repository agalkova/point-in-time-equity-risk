# Nasdaq-100 replication status

## 2026-10-23 — completed seven-year source-repaired run

The model, target, features, dates, and interpretation thresholds were frozen before the first
Nasdaq-100 evaluation. PtData then returned empty constituent lists before July 2023, making the
planned seven-year test impossible with that source alone. A partial 2023–2026 result was observed
before the membership source was repaired; this sequence is disclosed rather than calling the
entire workflow untouched.

## Membership source repair

- The replacement is `thuningxu/sp500nq100`, a public reconstruction from constituent-change
  tables, pinned at commit `1cc1de2770874293597a418b41b079e5337b260c` and SHA-256
  `c7de3905bfdd228eefbd3c7df1539a1178bee9006a04688fb319314a646e18e8`.
- The external CSV is downloaded locally and is not redistributed by this repository.
- It contains effective-date full-roster snapshots. Expansion over the planned window produced
  192,453 daily membership rows and 166 unique evaluation-period tickers.
- Across 39 shared PtData month-end snapshots, mean roster Jaccard similarity was 0.977 and the
  minimum was 0.870. The largest differences were in index-change months, consistent with PtData
  reflecting some changes one snapshot later.
- Dated `FB/META`, `CTRP/TCOM`, and `NLOK/GEN` provider mappings preserve historical security
  identity. Median in-membership price coverage is 100%.
- Alpaca returned 279,467 adjusted SIP bars. `FB` is reported missing as a direct request because
  its complete history is supplied through Alpaca's `META` series.

## Full 2020–2026 results

- 21,883 eligible stock-date observations and 4,422 severe-drawdown events.
- ROC AUC: **0.653**.
- Average precision: **0.301**, or **1.49×** the 0.202 event prevalence.
- Mean daily rank IC: **0.219**, with 40-day block interval **[0.162, 0.271]**.
- Highest-risk-decile event rate: **36.88%** versus **10.41%** in the lowest decile, a
  **3.54×** risk ratio.
- Annual rank IC was positive in all seven calendar years from 2020 through partial 2026.
- All four pre-specified full-universe thresholds passed.

## Independence limitation

Average daily NDX/S&P 500 membership overlap was 81.5%. Among 4,740 observations whose ticker was
not an S&P 500 member that day, ROC AUC was 0.617 and average-precision lift was 1.30×, but mean
daily rank IC was negative over only 53 qualifying daily cross-sections. That diagnostic is mixed
and does not establish clean independent-security transfer.

The defensible conclusion is that the unchanged drawdown-risk model transferred across time and
to the full Nasdaq-100 cross-section under the frozen criteria. A less-overlapping universe such
as the S&P 400 remains the appropriate next independent test.

## Reproduction

```bash
.venv/bin/python scripts/download_ndx_membership.py
.venv/bin/python scripts/build_ndx_public_membership.py
.venv/bin/python scripts/download_ndx_alpaca.py
.venv/bin/python scripts/run_ndx_replication.py
```
