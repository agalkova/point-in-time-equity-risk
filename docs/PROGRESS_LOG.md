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

## 2026-10-26 — immutable model release and end-to-end operations test

Completed:

- Fixed the freshness contract so an ordinary daily run compares the newest observation with the
  actual current date; an old local snapshot can no longer present itself as fresh.
- Separated training from inference and added immutable, checksum-verified model artifacts with an
  atomic active-model pointer.
- Bound every operational run to code, model, feature-schema, and source-data fingerprints.
- Enforced standards-compliant JSON by rejecting non-finite values at publication boundaries.
- Added explicit failure when drift cannot be measured and preserved fail-closed signal behavior.
- Added a credential-free synthetic integration test covering features, registration/loading,
  scoring, monitoring, and atomic publication.
- Verified a historical S&P 500 replay with one authorized signal and an identical idempotent
  retry; verified that a current-date run rejects the 2026-09-30 local snapshot as stale.

Operational interpretation:

- Daily scoring now consumes a promoted release rather than producing a newly trained model.
- CI covers the complete operational path without relying on private data or external services.
- The project demonstrates model governance and reproducible batch inference, not just research.

## 2026-10-26 — live data refresh and scheduled operations

Completed:

- Added a delayed-SIP S&P 500 refresh with a 400-calendar-day overlap and full point-in-time
  membership reconstruction.
- Staged and validated every replacement before publishing; added multi-file rollback behavior so
  an interrupted update does not leave a mixed bars/membership state.
- Added non-blocking run locks, retained orchestration receipts, nonzero failure propagation, and
  optional private HTTPS webhook alerts.
- Added a renderer for a weekday 6:15 p.m. macOS schedule without silently installing it.
- Refreshed the live panel through 2026-10-23: 1,860 trading days, 503 current members, and 100%
  latest-member price coverage.
- Confirmed all data-quality gates passed with three-day weekend staleness and 335 recent episodes.
- Preserved fail-closed behavior when score PSI reached 0.684; no signal was emitted.

Operational interpretation:

- The stale-data problem is resolved using the free delayed-SIP entitlement.
- The remaining live failure is model-regime drift, not a broken download or incomplete universe.
- Any response to that drift must be treated as a new model release, not a threshold adjustment.

## 2026-10-26 — modern challenger and shadow deployment

Completed:

- Froze two modern logistic-hazard candidates, their 2025 selection rule, 2026 evaluation, transfer
  diagnostics, and promotion thresholds before generating results.
- Selected the 2022–2024 rolling candidate over the 2020–2024 expanding candidate on 501 validation
  episodes.
- On 394 mature 2026 S&P 500 episodes, achieved 0.699 ROC AUC, 1.810× precision lift, 0.152 Brier
  score, and a 7.25× top/bottom-quintile event ratio.
- Passed absolute discrimination, calibration-tolerance, drift, and both transfer-universe gates.
- Reduced current score PSI from 0.684 to 0.118, approximately an 83% reduction.
- Withheld promotion because precision-lift improvement versus the champion was 0.014× rather than
  the frozen 0.05× requirement.
- Registered the selected model under an immutable `SHADOW` pointer and retained per-onset shadow
  risk curves without granting signal authority.
- Replaced repeat-every-run notifications with state-aware new-failure/change/recovery alerts.

Interpretation:

- The operational drift is consistent with market-regime change and legacy-model aging, not a
  broken feed or incomplete membership panel.
- The shadow model is materially more stable and predictively credible, but the frozen governance
  contract correctly prevents calling a modest incremental improvement a release victory.

## 2026-10-27 — official SEC archive fundamentals pilot

Completed:

- Downloaded the official 2024 Q1 SEC Financial Statement Data Set through the ordinary SEC data
  page after API and scripted archive requests returned HTTP 403.
- Added a disk-conscious parser that streams the archive, filters co-registrant and dimensional
  facts, preserves CIK/accession/source tags, and uses the actual filing date.
- Tested 30 unique issuers across all 11 GICS sectors and reconciled all six derived features to
  their accounting inputs with zero discrepancies or range flags.
- Raised gross-margin coverage by deriving gross profit from cost of revenue and raised leverage
  coverage by deriving liabilities from assets minus equity when direct tags were absent.
- Measured 63.3%–100% individual-feature coverage, 46.7% universal complete-case coverage, and
  56.0% nonfinancial complete-case coverage.
- Stopped before 2014–2026 expansion because the universal schema missed the frozen 50% gate.

Interpretation:

- Official direct SEC data is now a viable source; the remaining limitation is sector-specific
  accounting structure and historical CIK identity coverage.
- The next defensible step is a frozen sector-aware schema, not median imputation or selective
  deletion of inconvenient sectors.

## 2026-10-27 — sector-aware fundamentals and historical SEC identity

Completed:

- Froze separate nonfinancial, Financials, and Real Estate feature schemas with actual filing-date
  availability and no structural median filling.
- Added comparative revenue from the same filed 10-K, plus net margin, equity/assets,
  cash-flow/assets, and revenue-growth calculations.
- Re-ran the 30-company SEC archive pilot: schema complete-case coverage is 56%, 100%, and 100%,
  respectively; the two 100% results have only three and two issuers and remain provisional.
- Built 731 historical membership intervals and resolved them to permanent SEC CIKs using current
  constituents, the official SEC ticker registry, and decisive filing-name matches.
- Resolved 628 intervals covering 94.21% of membership-days; retained 103 uncertain intervals in a
  review queue rather than guessing through ticker reuse, acquisitions, or weak name matches.
- Passed the 90% staged-download gate but kept fundamentals disabled because 85.91% interval
  coverage remains below the frozen 95% model-enablement gate.

Next action:

- Process SEC quarterly archives chronologically and use each archive's issuer names to shrink the
  historical identity review queue before any fundamental model comparison.

## 2026-10-27 — first historical SEC archive block

Completed:

- Validated and processed all sixteen quarterly archives from 2014 through 2017, together with the
  existing 2024 Q1 and 2026 Q1 checkpoints.
- Built a resumable per-quarter pipeline and a combined 3,352-filing panel covering 670 issuers.
- Verified zero duplicate accessions, zero unparsed filing/period dates, and zero filings dated
  before their fiscal period end.
- Improved permanent-CIK resolution from 630 to 690 of 731 membership intervals; resolved intervals
  represent 97.57% of membership-days, while 94.39% interval coverage remains five resolutions
  short of the frozen model gate.
- Measured historical complete-case coverage of 41.1% for nonfinancials, 52.5% for Financials, and
  73.1% for Real Estate. The older data therefore overturned the small pilot's optimistic
  nonfinancial coverage result.

Interpretation:

- The identity design is working and is close to its gate.
- The nonfinancial schema is not yet historically robust; gross margin and cash-flow margin are the
  primary missing inputs. No model should be fit until the remaining quarters establish whether
  this persists across 2018–2025.
- Historical sector labels remain unavailable for former constituents; SEC SIC is used only to
  select an accounting schema, not presented as true historical GICS.

## 2026-10-27 — 2018–2021 SEC archive block

Completed:

- Added all sixteen quarterly archives from 2018 through 2021 to the resumable historical panel.
- Preserved prior CIK resolutions and earlier quarter outputs after their raw source ZIPs were
  removed; added an automated carry-forward test for this cumulative contract.
- Expanded the panel to 5,801 filings and 679 issuers with zero duplicate accessions, date parsing
  failures, or filings dated before their fiscal period end.
- Resolved 698 of 731 membership intervals, covering 98.06% of membership-days and 95.49% of
  intervals. The frozen historical identity gate now passes.
- Improved complete-case coverage to 46.7% for nonfinancials, 57.4% for Financials, and 78.5% for
  Real Estate. Nonfinancial coverage passes annually from 2019 onward but remains below 50% across
  the partial full-period panel.

Interpretation:

- Identity resolution is no longer the reason the fundamental model is disabled.
- The remaining decision depends on the 2022–2025 archive block and the nonfinancial missingness
  contract; changing the research start date after observing coverage would require a new frozen
  specification rather than an undocumented exclusion.

## 2026-10-27 — complete 2014 Q1–2026 Q3 SEC archive history

Completed:

- Processed all 51 quarterly SEC Financial Statement Data Set archives from 2014 Q1 through 2026
  Q3 into a compact 7,815-filing, 683-issuer panel.
- Verified zero duplicate accessions, unparsed filing dates, or filings dated before their fiscal
  period end.
- Tightened historical identity matching after audit examples exposed time-inconsistent ticker
  reuse and an Alexion/Lexicon look-alike; filing-name matches now require membership-time overlap
  and exact agreement on a distinctive name anchor.
- Resolved 699 of 731 intervals, covering 98.15% of membership-days and 95.62% of intervals. The
  identity gate passes without accepting the detected false matches.
- Achieved complete-case coverage of 50.1% for nonfinancials, 61.6% for Financials, and 82.7% for
  Real Estate. All frozen archive-stage coverage gates pass.

Interpretation:

- The historical SEC archive and issuer-identity foundation is complete enough to advance.
- The nonfinancial gate passes by only 0.06 percentage points, so missingness must remain explicit
  and sensitivity analysis is mandatory.
- SIVB was safely resolved in the final block; its 2022–2023 filings are present, while earlier
  filings remain a documented one-company backfill gap.
- The next stage is a filing-date-safe as-of join to the research episodes, followed by historical
  sector-treatment and coverage audits before any model is enabled.

## 2026-10-27 — point-in-time SEC fundamental ablation

Completed:

- Froze the v1.4 join, freshness, missingness, model, validation, and portfolio rules before fitting
  the expanded fundamental models.
- Replaced ticker-only joins with membership-interval CIK joins and actual filing-date as-of joins;
  stale annual filings expire after 550 days.
- Built a 41,240-row monthly panel with 98.33% identity coverage, 97.37% usable filing coverage,
  97.06% quality-score coverage, and zero future-filing timing violations.
- Preserved missing values for unresolved identities and the known SIVB backfill gap rather than
  substituting later statements.
- Ran price-only, fundamentals-only, and combined ridge/gradient-boosting ensembles on 34,184
  identical out-of-fold observations across 68 months and six expanding yearly tests.
- The combined ensemble improved mean rank IC by 0.0056, but its paired block interval was
  [-0.0294, 0.0336]; the improvement occurred in only three of six years and two of three accounting
  schemas, so the frozen directional gate failed.
- The combined long-only portfolio returned 13.16% annually with a 0.64 Sharpe versus 10.52% and
  0.58 for price-only, but had higher risk and statistically weak 1.66% six-factor alpha
  (HAC t=0.52).
- Post-specification long-short diagnostics were negative after costs, rejecting a market-neutral
  alpha interpretation.
- Added point-in-time identity, no-leakage, filing-expiry, missing-rank, and quality-direction tests;
  the full suite now passes 84 tests.

Interpretation:

- The official SEC archive pipeline is a strong portfolio-quality data-engineering contribution.
- Fundamentals provide a modest research signal, especially in the transparent ridge model, but
  the effect is unstable and does not establish alpha.
- Further tuning on the same holdout is not justified. A frozen simpler candidate needs prospective
  or independent-market confirmation.

## 2026-10-27 — public release hardening

Completed:

- Rewrote the README around the primary research question, three strongest results, system design,
  reproduction path, and explicit claim boundaries.
- Replaced the broad résumé list with role-specific quantitative-research and data-engineering
  bullets tied to measured results.
- Added a deterministic public demonstration with 4,320 synthetic OHLCV rows, chronological
  training and test samples, and an explicit non-research disclaimer.
- Added a Makefile target that runs focused linting, all 84 tests, the synthetic pipeline, and a
  public-repository audit.
- Expanded CI to reproduce the synthetic data byte-for-byte and validate the SEC point-in-time
  components.
- Added release checks for credentials, vendor or derived datasets, oversized files, broken README
  links, machine-specific paths, and synthetic-data labeling.
- Preregistered the unchanged S&P 400 combined-ridge transfer test with coverage and performance
  gates. The test is marked not run because the SEC archives must first be reprocessed for S&P 400
  CIKs.

Release status:

- `make verify` passes.
- The public tree contains no vendor datasets or credential files.
- The repository is ready for review or publication after the owner chooses the destination and
  commits the current changes.

