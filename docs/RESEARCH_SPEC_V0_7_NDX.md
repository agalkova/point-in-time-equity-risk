# v0.7 Nasdaq-100 cross-universe replication

Status: frozen before membership retrieval and model evaluation  
Created: 2026-10-22

## Question

Does the unchanged v0.1 S&P-developed drawdown-risk model retain useful ranking power when the
feature cross-section and market-regime variables are rebuilt inside the Nasdaq-100?

## Model lock

- Use the exact v0.1 eligibility rule: 60-day return at least 20% and price within 10% of its
  trailing 60-day high.
- Use the exact 40-trading-day, -15% forward drawdown event.
- Use the exact feature schema and logistic model selected on legacy validation.
- Refit only as already specified: all legacy train, validation, and test observations.
- Do not alter coefficients, thresholds, features, imputation, or scaling after NDX results exist.

## Universe and data

- Nasdaq-100 (`NDX`) constituent snapshots from PtData's point-in-time index endpoint.
- Month-end snapshots from 2019-06 through 2026-09, expanded forward to business days.
- Alpaca SIP daily bars with `adjustment=all` over 2019-06-01 through 2026-09-30.
- Evaluation period 2020-01-01 through 2026-09-30, requiring a complete 40-day target.

The free source provides dated snapshots, not a licensed effective-date change history. Membership
changes within a month can therefore be reflected with delay until the next snapshot. This is a
known approximation and must be reported.

## Independence limitation

The Nasdaq-100 overlaps materially with the S&P 500. This is a cross-universe replication, not a
fully independent-security test. The report must quantify daily overlap and separately summarize
NDX observations whose ticker was not an S&P 500 member on that date when sample size permits.

## Locked outputs

- ROC AUC and average precision/lift
- Mean daily rank IC with 40-day block interval
- Risk-event rate by predicted decile
- Highest-minus-lowest decile event-rate spread with block interval
- Annual stability
- Membership/price coverage and NDX/S&P overlap

## Interpretation rule

Replication is considered supportive if full-NDX ROC AUC exceeds 0.60, top-decile event rate is
at least twice bottom-decile event rate, mean rank IC is positive with a block interval excluding
zero, and annual rank IC is positive in at least six of seven calendar years. The non-S&P subset
is reported as a limited-sample diagnostic, not a pass condition.
