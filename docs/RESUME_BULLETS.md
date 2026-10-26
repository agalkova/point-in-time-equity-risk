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
- Reframed hindsight-labeled bubble detection as a two-stage exuberance-to-drawdown hazard
  model; evaluated 8,464 distinct episode onsets across three point-in-time universe runs,
  producing 1.45×–1.57× 40-day precision lift and 2.45×–3.50× top/bottom-quintile risk ratios.
- Pre-specified and rejected two plausible follow-ups: annual probability recalibration worsened
  Brier score, while a cost-aware high-risk exclusion reduced drawdown but also reduced Sharpe
  across all three universes—demonstrating disciplined negative-result reporting.
- Productionized daily risk inference across three universes with unlabeled feature generation,
  an immutable checksum-verified model registry, coverage/freshness gates, PSI drift monitoring,
  code/model/data lineage, fail-closed signal suppression, atomic publication, byte-verifiable
  idempotent retries, transactional data refresh with rollback, concurrency locks, failure alerts,
  local scheduling, and credential-free end-to-end CI.
- Built a governed champion–challenger release process: diagnosed market-regime drift, reduced
  output PSI from 0.684 to 0.118 with a modern rolling hazard model, validated it across three
  universes, and deployed immutable shadow scoring while withholding promotion after one frozen
  incremental-performance criterion failed.
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
> replication across 2020–2026. I then returned to the original bubble idea with a discrete-time
> hazard model that produces 10/20/40/60-day early-warning risk curves at episode onset rather
> than labeling an entire episode after its crash is already known.
