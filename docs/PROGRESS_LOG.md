# Progress log

## 2026-10-22 — SEC fundamentals proof of concept

- Froze the v0.5 pilot before observing any fundamental-model result.
- Implemented official SEC Companyfacts ingestion and annual US-GAAP normalization.
- Added filing-date-aware as-of joins and automated lookahead tests.
- Added eight quality, profitability, growth, accrual, and leverage features.
- Added matched price-only, fundamentals-only, and combined expanding walk-forward tests.
- Added cost-aware pilot portfolios and six-factor attribution.
- All 28 repository tests pass; checks for the new files pass.
- The SEC returned HTTP 403 from this execution environment for both Companyfacts and the
  official bulk archive. No issuer data was downloaded and no empirical result was claimed.
- The project owner reproduced the SEC 403 from a normal Terminal. Before observing results,
  added a no-key PtData fallback that preserves SEC source accessions and knowledge timestamps,
  plus explicit third-party-provider limitations.
- Completed 176 fallback queries and normalized 170 annual issuer-year records for 22 companies.
- Ran 1,219 out-of-fold observations over 56 month-ends. Combined rank IC improved from 0.0025
  to 0.0168, but the paired lift interval was [-0.0318, 0.0694] and the portfolio deteriorated.
- Rejected this fundamental feature set without post-result tuning and documented the outcome in
  `docs/FUNDAMENTAL_RESULTS.md`.
- Froze and ran a constrained portfolio optimizer around the unchanged ridge scores. It failed all
  four pass conditions: return fell to 13.97%, Sharpe to 0.81, drawdown worsened to -21.49%, and
  estimated factor alpha fell to -0.23%.
- Preserved equal-weight ridge top-50 as the sole prospective candidate rather than tuning the
  failed optimizer.
- Added immutable prospective signal snapshots, SHA-256 content hashes, a unique-date ledger,
  turnover/cost records, and tests preventing silent replacement of prior evidence.
- Confirmed the latest 2026-09-30 signal remains pre-freeze shadow output; the prospective ledger
  correctly contains no eligible observation yet.
- Froze v0.7 for an unchanged-model Nasdaq-100 cross-universe replication, including explicit
  month-end membership and S&P-overlap limitations.
- Added resumable point-in-time NDX membership ingestion, separate Alpaca SIP ingestion, identity
  checks, overlap diagnostics, non-S&P subset reporting, and locked pass criteria.
- Retrieved all 88 requested NDX responses and discovered that the free provider returned empty
  membership lists for the 49 months before July 2023; recorded this as a source-coverage limit.
- Downloaded 217,527 adjusted SIP bars for all 123 tickers with no missing symbols.
- Ran the untouched model on 9,242 eligible NDX observations. It achieved 0.663 ROC AUC, 1.57x
  average-precision lift, 0.226 mean daily rank IC, and a 4.29x top/bottom risk ratio.
- Marked the seven-year pass decision not evaluable rather than counting unavailable years as
  failures. All three measurable frozen thresholds passed, and all 33 repository tests pass.
- Results and limitations are recorded in `docs/NDX_REPLICATION_STATUS.md`.
- Repaired the incomplete NDX membership source with a checksum-pinned public reconstruction;
  its 39-date overlap with PtData averaged 0.977 Jaccard similarity.
- Expanded the NDX evaluation to the planned 2020–2026 period: 21,883 observations, 0.653 ROC
  AUC, 1.49x average-precision lift, 0.219 mean daily rank IC, and a 3.54x top/bottom risk ratio.
- The unchanged model passed all four frozen full-universe criteria, including positive annual
  rank IC in all seven years. Recorded the 81.5% S&P overlap and mixed non-S&P diagnostic.
- Froze v0.8 before data retrieval as an independent S&P 400 MidCap replication with source and
  price quality gates plus five predictive pass criteria.
- Built 766,141 point-in-time daily membership rows from a checksum-pinned public reconstruction,
  rejected two non-security markup artifacts, resolved eight ticker lineages, and recovered 6,950
  dated historical bars for 17 low-coverage names.
- Evaluated 85,587 eligible mid-cap observations with only 0.33% average S&P 500 overlap. The
  unchanged model achieved 0.654 ROC AUC, 1.49x average-precision lift, 0.182 mean daily rank IC,
  and a 2.98x top/bottom risk ratio.
- Both data-quality gates and all five predictive criteria passed; annual rank IC was positive in
  all seven years.

## 2026-10-21

Completed:

- Audited the original notebooks and datasets without modifying them.
- Replaced hindsight bubble membership with a forward 40-day drawdown target.
- Ran a chronological train, validation, and legacy-test feasibility study.
- Added factor comparisons, alternate target definitions, annual stability checks, and a 40-day moving-block bootstrap.
- Rejected an immediate alpha claim after a naïve daily exclusion portfolio failed.
- Created this separate project with a frozen specification and decision log.
- Added the first Alpaca historical SIP client and data-audit foundation.
- Reproduced the recorded feasibility metrics exactly from the modular package.
- Added 13 passing tests covering target timing, sample isolation, legacy data contracts, response normalization, reconciliation, and refusal of IEX data.
- Added raw-versus-adjusted overlap reconciliation for price levels, returns, consolidated volume, coverage dates, and ticker mappings.
- Downloaded raw and fully adjusted Alpaca SIP pilot data for 20 securities over 2016-01-01 through 2019-06-12.
- Reconciled 16,810 overlapping security-date records with no missing requested symbols, including renamed and delisted names.
- Confirmed that raw Alpaca closes are the closest level match to the legacy price field for all 20 pilot securities.
- Confirmed strong provider agreement: median raw-return correlation 0.9994, median adjusted-return correlation 1.0000, and median raw-volume correlation 0.9905.
- Added automatic loading of the private, Git-ignored project `.env` file for downloads.
- Reconstructed 2019–2026 point-in-time S&P 500 membership from 412 public constituent changes.
- Downloaded 1,101,390 adjusted Alpaca SIP bars for 642 returned symbols and a separate SPY benchmark.
- Added dated corporate-action chains and historical `asof` requests, including protection against an unrelated reuse of ticker `STI`.
- Opened the frozen modern holdout once: 91,299 observations, 0.671 ROC AUC, 1.73× average-precision lift, and 18.84 percentage points of top-minus-bottom decile separation.
- Confirmed positive risk separation in every modern calendar year.
- Completed weekly and monthly cost-aware portfolio tests. The return optimizer selected no risk penalty; the monthly exclusion overlay reduced risk but also return and exposure.
- Added 18 passing tests, CI, publication figures, a results report, and resume bullets.

## 2026-10-22

Completed:

- Froze an explicitly exploratory v0.2 specification while preserving v0.1 as the
  confirmatory result.
- Expanded the research panel to 31 price, volume, liquidity, tail-risk, path, and
  market-state features.
- Added seven expanding calendar-year folds with a 40-trading-day purge and 91,299
  out-of-fold modern predictions.
- Compared regularized logistic regression, histogram gradient boosting, a fixed 50/50
  ensemble, and a transparent four-factor composite.
- Added calibration error, yearly stability, permutation importance, non-overlapping
  event evaluation, warning precision/recall, and first-breach lead time.
- Added a cash-matched portfolio diagnostic using walk-forward risk scores. The filter did
  not improve return, Sharpe, or maximum drawdown versus ordinary momentum at the same
  realized daily exposure.
- Expanded the automated suite to 23 tests and added four publication figures.

Current interpretation:

- The advanced workflow strengthens the evidence for a cross-sectional drawdown-risk rank.
- The nonlinear model does not dominate; the ensemble is modestly stronger on probabilistic
  metrics, while the transparent composite remains competitive.
- The exposure-matched result rejects the stronger portfolio claim. This is not a hidden
  alpha strategy, and the repository should say so plainly.

Alpha research extension:

- Froze v0.3 before execution with a beta-adjusted 21-day return target, 22 fixed features,
  monthly signals, six yearly walk-forward folds, and 10 basis-point one-way costs.
- Added 33,598 out-of-fold security-month predictions across 68 month-end cross-sections.
- Rejected the primary ensemble alpha claim: 12.31% annual return, 0.68 Sharpe, and -1.12%
  estimated annual six-factor alpha versus 14.78% and 0.89 for SPY.
- Identified a post-spec ridge candidate with 21.34% annual return, 1.19 Sharpe, -18.83%
  maximum drawdown, and 5.48% estimated annual factor alpha; its 1.46 alpha t-statistic is
  insufficient for a confirmed claim.
- Confirmed that the ridge estimate remains economically positive across 25, 50, and 100
  positions and 5–20 basis-point transaction-cost assumptions, but no sensitivity reaches
  a 2.0 alpha t-statistic.
- Froze the ridge top-50 candidate for future month-end observation without retroactively
  promoting it to the primary specification.
- Expanded the automated suite to 26 passing tests.

Next actions:

1. Begin the v0.4 prospective record at the first month-end after the freeze date.
2. Optionally add licensed point-in-time sector data; do not infer historical sectors from current labels.
3. Create the GitHub remote only when authorized by the project owner.

## 2026-10-23 — exuberance episode hazard model

Completed:

- Revisited the original notebook’s buildup, abnormal-volume, and later-burst concept.
- Froze v0.9 before execution as a two-stage exuberance-onset and forward drawdown-hazard study.
- Replaced hindsight-confirmed episode labels with one prediction at each new episode onset.
- Added a pooled discrete-time logistic hazard model with monotonic 10-, 20-, 40-, and 60-day cumulative risk estimates.
- Trained on 2,696 legacy episodes and evaluated 8,464 modern episodes across the point-in-time S&P 500, Nasdaq-100, and S&P 400 panels.
- At 40 days, achieved 0.618–0.628 ROC AUC, 1.45×–1.57× average-precision lift, and 2.45×–3.50× highest/lowest-risk-quintile ratios.
- Beat trailing 60-day return alone in all three universes and measured 18–19 trading days of median lead time among high-risk true events.
- Diagnosed legacy-to-modern calibration drift rather than retrospectively altering the model.
- Expanded the automated suite to 41 passing tests and added a full results report, coefficient table, calibration table, episode predictions, and publication figure.

Current interpretation:

- The corrected model is a credible multi-horizon fragility-ranking system and is much closer to the original project’s intended story.
- It does not identify fundamental bubbles or establish alpha.
- Absolute live probabilities require a new, frozen walk-forward recalibration rule; current probability levels should not be taken literally.

## 2026-10-23 — calibration and economic-utility follow-up

Completed:

- Froze v1.0 before execution with an annual, prior-outcome-only intercept adjustment and a legacy-threshold episode exclusion overlay.
- Added explicit outcome-maturity cutoffs so no calibration year can use unresolved or future episode outcomes.
- Confirmed that recalibration left every within-year ROC AUC unchanged, as required by the fixed-slope design.
- Rejected recalibration after Brier score worsened in all three universes; log loss improved only in the Nasdaq-100 and S&P 400.
- Applied a fixed legacy 80th-percentile risk cutoff to 40-day post-signal episode cohorts with next-day entry and 10-basis-point one-way costs.
- Found lower volatility and maximum drawdown in all three overlay portfolios, but lower annual return and Sharpe in all three.
- Rejected the portfolio overlay without changing the threshold after inspection.
- Expanded the automated suite to 43 passing tests and documented the negative results as part of the final research narrative.

Final v1.0 interpretation:

- The score remains useful for relative fragility ranking.
- Neither the tested calibration rule nor the tested trading overlay met its frozen success criterion.
- Further historical tuning would add overfitting risk faster than portfolio value; future work should emphasize prospective evidence.

## 2026-10-23 — production orchestration and monitoring

Completed:

- Separated live feature inference from research labeling so the latest market date can be scored without requiring or fabricating future outcomes.
- Added one monitored command for S&P 500, Nasdaq-100, and S&P 400 episode-onset signals.
- Added hard gates for data history, latest membership coverage, staleness, and recent episode volume.
- Added score and feature PSI monitoring against a fixed 2024–2025 accepted operating reference.
- Added source-file, feature-schema, signal, and health-report SHA-256 hashes to each run manifest.
- Added atomic run publication, fail-closed empty outputs, code-revision identity, and byte-verifiable idempotent retries.
- Verified authorized WARN runs on all three universes for 2025-12-26; the S&P 500 emitted one onset signal and the S&P 400 emitted two.
- Verified that the 2026-09-30 S&P 500 run suppressed every signal when score PSI reached 0.521.
- Expanded the automated suite to 46 passing tests and added scoped production-code linting to CI.

Operational interpretation:

- This is now a reproducible research-to-batch-inference system rather than only a historical backtest repository.
- The runner deliberately creates signals and evidence but does not place orders.
- Production health failures are retained as evidence rather than bypassed to force output.

