# S&P 400 independent-universe replication

## Conclusion

The unchanged large-cap-developed drawdown-risk model transferred successfully to the S&P 400
MidCap universe. Both pre-evaluation data-quality gates and all five frozen predictive criteria
passed. Average daily overlap with the point-in-time S&P 500 universe was only 0.33%, making this
the project's strongest independent-universe validation.

This supports a cross-sectional drawdown-risk signal. It does not demonstrate expected-return
alpha or a directly tradable portfolio.

## Frozen design

- Specification: v0.8.0, committed before membership retrieval, price retrieval, or evaluation.
- Model: unchanged legacy-selected `logistic_C_0.01` pipeline.
- Eligibility: at least 20% trailing 60-day return and within 10% of the trailing high.
- Target: a loss of at least 15% within the next 40 trading days.
- Evaluation: 2020-01-02 through 2026-08-04, with complete forward targets.
- Inference: 40-day moving-block bootstrap.

## Data engineering result

- Pinned `pitindex` revision: `2df030e5c9be7c83cf4b28c3d8597d74d274757e`.
- 226 effective-date roster states, 753 valid historical tickers, and 766,141 daily membership
  rows over the requested window.
- Final reconstructed roster exactly matched the pinned 400-stock current roster.
- Two non-security source artifacts were rejected before evaluation.
- Eight historical ticker lineages were joined explicitly to successor price series.
- A fixed dated lookup recovered 6,950 bars for 17 initially low-coverage historical tickers.
- Final median in-membership price coverage was 100%; mean coverage was 99.74%.
- The panel contains 1,224,310 primary adjusted SIP bars plus the targeted historical recovery.

The membership data are a community reconstruction from public change tables and revision
history, not licensed official S&P constituent history. Revision-derived events can lag true
effective dates by up to roughly one month. Six acquired or delisted names remain below 95%
coverage because trading ended before the reconstructed removal date.

## Predictive results

| Metric | Result | Frozen threshold | Outcome |
|---|---:|---:|---|
| Eligible observations | 85,587 | — | — |
| Severe-drawdown events | 17,075 | — | — |
| ROC AUC | **0.654** | > 0.60 | Pass |
| Average-precision lift | **1.49×** | ≥ 1.25× | Pass |
| Mean daily rank IC | **0.182** | Positive interval | Pass |
| Rank-IC 95% block interval | **[0.146, 0.219]** | Lower bound > 0 | Pass |
| Highest-risk-decile event rate | **32.28%** | — | — |
| Lowest-risk-decile event rate | **10.85%** | — | — |
| Highest/lowest risk ratio | **2.98×** | ≥ 2.0× | Pass |
| Positive annual rank IC | **7 of 7 years** | ≥ 6 of 7 | Pass |

Annual rank IC remained positive in every year, including the partial 2026 sample. Year-specific
ROC AUC ranged from 0.597 in 2025 to 0.679 in 2022; the pooled conclusion is therefore supported by
stable ranking direction rather than uniformly strong discrimination in every regime.

## Interpretation

The S&P 500, Nasdaq-100, and S&P 400 results now tell a coherent story. The same transparent model
ranks severe forward drawdown risk across a modern large-cap holdout, a technology-heavy universe,
and a nearly non-overlapping mid-cap universe. The S&P 400 result materially reduces the concern
that the Nasdaq result merely repeated the same securities.

The next high-value work is repository publication and prospective observation. Repeatedly trying
new universes or strategy mappings after three supportive tests would add less credibility than
preserving this evidence trail.
