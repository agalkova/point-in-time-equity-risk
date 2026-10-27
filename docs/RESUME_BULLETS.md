# Resume and interview summary

Use the bullets that match the role. Keep two or three on a one-page résumé.

## Quantitative research

- Developed and out-of-time tested a cross-sectional equity drawdown-risk model on 91,299 S&P 500
  observations, achieving 0.671 ROC AUC, 1.73× average-precision lift, and an 18.8 percentage-point
  event-rate spread between the highest and lowest risk deciles.
- Replicated the frozen model without retraining on 85,587 point-in-time S&P 400 observations with
  0.33% average large-cap overlap, achieving 0.654 ROC AUC, positive annual rank IC in all seven
  years, and a 2.98× highest-to-lowest-decile event ratio.
- Built a filing-date-safe fundamental signal study over 34,184 out-of-fold stock-month
  observations; evaluated ridge and nonlinear models with expanding walk-forward folds,
  transaction costs, block-bootstrap uncertainty, and six-factor HAC attribution, and rejected the
  alpha claim when time stability and long-short tests failed.

## Data and quant engineering

- Engineered a point-in-time equity data pipeline over more than one million daily market bars,
  including historical index membership, dated symbol aliases, ticker-reuse controls,
  corporate-action lineage, coverage gates, and reproducible source manifests.
- Processed 51 SEC Financial Statement Data Set archives into 7,815 normalized annual filings;
  resolved historical issuer identity with permanent CIKs and built an as-of panel with 98.33%
  identity coverage, 97.37% fresh-filing coverage, and zero future-filing violations.
- Productionized daily risk inference with checksum-verified model artifacts, input and feature
  hashes, freshness and coverage gates, PSI drift monitoring, atomic publication, idempotent
  retries, and fail-closed signal suppression.

## Short interview description

> I started with a notebook that labeled bubbles using future crashes. I reframed the problem as
> forward drawdown-risk ranking, rebuilt the data around point-in-time membership and symbol
> history, and froze the evaluation before testing the modern period. The model produced a stable
> risk-ranking signal and transferred unchanged to a nearly non-overlapping S&P 400 universe. I
> later added a filing-date-safe SEC fundamentals pipeline and tested expected-return signals. Those
> results were promising in some long-only comparisons but did not support an alpha claim, which is
> documented as a negative result rather than tuned away.

## One-line project description

Point-in-time equity research and production-monitoring system combining market data, historical
index membership, corporate-action lineage, and SEC filings with leakage-controlled validation.
