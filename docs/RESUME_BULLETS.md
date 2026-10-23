# Resume bullets

Use one or two of these, adjusted to the space available:

- Built a point-in-time S&P 500 research pipeline over 1.1M Alpaca SIP daily bars, including
  historical membership reconstruction, corporate-action/ticker lineage, data contracts,
  and leakage tests across 640 securities.
- Developed and out-of-time tested a cross-sectional equity drawdown-risk model on 91K
  modern observations; achieved 0.671 ROC AUC, 1.73× average-precision lift, and a 18.8
  percentage-point event-rate spread between highest- and lowest-risk deciles.
- Independently replicated the unchanged model on 85K point-in-time S&P 400 observations with
  0.33% large-cap overlap, achieving 0.654 ROC AUC, 1.49× precision lift, positive rank IC in all
  seven years, and a 2.98× highest/lowest-risk-decile event ratio.
- Designed a transaction-cost-aware momentum portfolio experiment with weekly/monthly
  rebalancing, 2% position caps, validation-only hyperparameter selection, and explicit
  negative-result reporting against SPY and factor baselines.
- Built a 31-feature, purged walk-forward model comparison across seven calendar-year
  folds, adding calibration, non-overlapping event/lead-time analysis, permutation
  importance, and a cash-matched portfolio diagnostic backed by 23 automated tests.
- Built a separate 22-feature expected-return research layer with 33K walk-forward
  security-month predictions, cost-aware long-only/long-short simulation, six-factor HAC
  attribution, and an explicitly frozen prospective candidate after rejecting the primary
  ensemble's alpha claim.

Interview summary:

> I inherited a notebook that used hindsight-defined bubble labels. I reframed it as a
> forward drawdown-risk problem, rebuilt the data pipeline around point-in-time membership,
> froze the experiment before opening the modern holdout, and found a real risk-ranking
> signal—but not a standalone alpha strategy. The most valuable part is the research design
> and data engineering, including catching ticker reuse and source markup before they contaminated
> the tests. The unchanged model subsequently passed a frozen, nearly non-overlapping S&P 400
> replication across 2020–2026.
