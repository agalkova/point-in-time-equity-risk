# v0.8 S&P 400 independent-universe replication

Status: frozen before membership retrieval, price retrieval, and model evaluation  
Created: 2026-10-23

## Question

Does the unchanged v0.1 large-cap-developed drawdown-risk model retain ranking power in the S&P
400 MidCap universe from 2020 through 2026?

This test is intended to address the Nasdaq replication's 81.5% average overlap with the S&P 500.
S&P 400 membership should be materially more independent of the development universe.

## Locked model and target

- Use the exact v0.1 eligibility rule: 60-day return at least 20% and price within 10% of its
  trailing 60-day high.
- Use the exact 40-trading-day, -15% forward drawdown event.
- Use the exact legacy-selected `logistic_C_0.01` feature schema and refit procedure.
- Do not change coefficients, features, thresholds, target, imputation, or scaling after results
  exist.

## Data

- S&P 400 point-in-time membership from the checksum-pinned `pitindex` public reconstruction.
- Effective-date changes expanded forward to business days from 2019-06-01.
- Alpaca SIP daily bars with `adjustment=all` through 2026-09-30.
- Evaluation from 2020-01-01 through the last signal with a complete 40-day target.

The free membership source combines public change tables and revision-history diffs. Recovered
revision events can lag true index-effective dates by up to roughly one month. It is not licensed
official S&P constituent history. The exact source revision, file hashes, reconciliation, ticker
coverage, and missing-symbol handling must be reported.

The pinned event file contains one literal Wikipedia-template artifact,
`TEMPLATE:INVESTORS EXCHANGE LINK`, during 2019. It is explicitly excluded as a non-security
record before price retrieval. This was discovered by the ticker-format gate before any model
result was observed.

## Pre-evaluation quality gates

- Event-sourced final roster versus the pinned current roster: Jaccard similarity at least 0.95.
- Median in-membership adjusted-price coverage: at least 0.95.
- Fail closed on implausible roster sizes or malformed add/remove events.

No predictive conclusion may be reported if a quality gate fails.

## Locked metrics

- ROC AUC and average precision/lift.
- Mean daily rank IC with a 40-day moving-block interval.
- Highest- versus lowest-risk-decile event rates and ratio.
- Annual stability from 2020 through partial 2026.
- Daily overlap with the point-in-time S&P 500 universe.
- Membership and price coverage.

## Interpretation rule

Replication is supportive only if all quality gates pass and full-universe ROC AUC exceeds 0.60,
average-precision lift is at least 1.25, highest/lowest-decile risk ratio is at least 2.0, the
rank-IC block interval excludes zero, and annual rank IC is positive in at least six of seven
calendar years.

This is a prediction-transfer test, not an alpha or tradability claim.
