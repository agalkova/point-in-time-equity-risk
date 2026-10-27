# Point-in-time SEC fundamental ablation

## Question

Do annual SEC fundamentals add out-of-sample information to the existing monthly price-and-volume
return model when issuer identity, filing availability, missingness, and the investment universe are
handled point in time?

The v1.4 rules were frozen before this comparison. Permanent SEC CIK identifiers replace ticker-only
joins, statements become usable on their actual filing date, filings expire after 550 days, and
observed ratios are ranked within date and accounting schema before any model-level imputation.
Historical GICS classifications are unavailable for former constituents, so the analysis makes the
narrower claim of accounting-schema normalization rather than historical sector neutrality.

## Data and timing audit

- 41,240 eligible stock-month observations across 82 signal dates from January 2020 through October
  2026
- 98.33% point-in-time issuer-identity coverage
- 97.37% filing coverage after the 550-day freshness limit
- 97.06% coverage for the four-feature minimum quality score
- zero filings joined before their public filing date
- 20 stale filing observations expired rather than carried indefinitely
- 38 SIVB observations, including 26 intentionally missing earlier filings; no later statement was
  backfilled into an earlier signal date

The model comparison uses 34,184 out-of-fold observations and 68 months from 2021 through August
2026. Price-only, fundamentals-only, and combined models use identical rows and expanding yearly
walk-forward folds with a one-signal purge.

## Predictive results

| Frozen comparison | Mean monthly rank IC | 21-day top-minus-bottom residual return | Block interval for rank IC |
| --- | ---: | ---: | ---: |
| Price ensemble | -0.0005 | -0.03% | [-0.0296, 0.0363] |
| Fundamental ensemble | 0.0168 | 0.46% | [-0.0154, 0.0488] |
| Combined ensemble | 0.0051 | 0.26% | [-0.0214, 0.0308] |
| Fundamental ridge | 0.0181 | 0.42% | [-0.0146, 0.0521] |
| Combined ridge | 0.0101 | 0.58% | [-0.0170, 0.0377] |

The frozen combined ensemble improves mean rank IC over the price ensemble by 0.0056, but the paired
block interval is [-0.0294, 0.0336]. The improvement is positive in 2021–2023 and negative in
2024–2026. It is positive for nonfinancial and Real Estate issuers but negative for Financials.
The pre-specified directional gate therefore fails.

The simpler ridge results are a useful research lead: fundamentals-only ridge has the strongest
pooled rank IC, and combined ridge has the largest top-minus-bottom residual-return spread. They are
reported as model diagnostics, not promoted after inspection to replace the frozen ensemble.

## Portfolio results

All primary portfolios hold the top 50 names, rebalance monthly, remain fully invested, and charge
10 basis points one way.

| Primary long-only portfolio | Annual return | Sharpe | Maximum drawdown | Six-factor alpha | HAC t-statistic |
| --- | ---: | ---: | ---: | ---: | ---: |
| Price ensemble | 10.52% | 0.58 | -30.65% | -2.13% | -0.59 |
| Fundamental ensemble | 13.26% | 0.64 | -35.47% | 1.61% | 0.58 |
| Combined ensemble | 13.16% | 0.64 | -33.82% | 1.66% | 0.52 |

The fundamental and combined portfolios earn higher returns than the matched price portfolio, but
with greater volatility, deeper drawdowns, market beta above one, and statistically weak estimated
factor alpha. Post-specification long-short diagnostics lose money after costs; the combined version
returns -1.64% annually and has -0.99% estimated annual factor alpha. This is direct evidence against
calling the result a market-neutral alpha strategy.

## Decision

The expanded SEC data succeeds as a data-engineering and point-in-time research system. Fundamentals
show a small, economically interesting signal—especially in the transparent ridge model—but do not
pass the frozen stability test and do not establish alpha. The correct portfolio claim remains:

> Filing-date-safe SEC fundamentals modestly improve some out-of-sample ranking and long-only
> portfolio diagnostics, but the effect is unstable, statistically uncertain, and absent in the
> post-specification long-short test.

The next defensible research step is not more tuning on the same 2021–2026 holdout. It is to freeze a
simpler ridge-based candidate, obtain historical sector classifications or use a broader universe,
and evaluate it prospectively or on an independent market.

## Reproduction

```bash
python scripts/build_point_in_time_fundamental_panel.py
python scripts/run_point_in_time_fundamental_ablation.py
```

Machine-readable outputs are written to `reports/tables/v14_point_in_time_fundamental_audit.json`,
`reports/tables/v14_fundamental_ablation_summary.json`, and the corresponding walk-forward,
prediction, and daily portfolio tables.
