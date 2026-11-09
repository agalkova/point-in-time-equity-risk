# v0.5 SEC fundamentals proof of concept

## Purpose

Test whether point-in-time annual financial-statement signals add out-of-sample ranking
information beyond the frozen price-and-volume alpha feature set. This is an engineering and
signal-value pilot, not a new alpha claim.

## Frozen pilot universe

The pilot selects the first two unique-CIK issuers alphabetically in each current GICS sector,
after limiting the current constituent table to companies added to the S&P 500 by 2018-12-31.
This deterministic rule uses no return outcome. It produces approximately 22 issuers.

Because the selection begins from the current constituent table, it has survivor bias. Pilot
portfolio returns are diagnostic only and cannot be generalized to a historical investable
universe.

## Source and timing rule

The preferred source is the SEC Companyfacts API. The SEC edge returned HTTP 403 from both the
execution environment and the project owner's network before any observation was retrieved.
Before observing model results, v0.5.1 therefore added a fallback to PtData's no-key point-in-time
endpoint. PtData reports SEC EDGAR XBRL Companyfacts as its upstream source and returns a source
accession plus `knowledge_from` timestamp for every metric. Raw responses are retained for audit.

This third-party normalization dependency is a material limitation and is identified in every
manifest and result. It is preferable to pretending that a conservatively lagged, currently
restated statement is true point-in-time data.

A value becomes available on its returned knowledge date, never at its fiscal-year label. At
each month-end signal, the pipeline performs a backward as-of join to the latest statement known
on that date. Automated tests fail if a post-signal statement enters a feature row.

The fallback retrieves annual fiscal years 2018–2025. When component metrics carry different
knowledge dates, the entire feature row is delayed until the latest component date, a conservative
rule ensuring that every value was public.

## Signals

- Gross, operating, and net margins
- Operating cash flow divided by absolute net income
- Accrual ratio: net income minus operating cash flow, divided by revenue
- Annual revenue growth
- Symmetric annual growth in gross profit, operating income, and operating cash flow
- Diluted-share growth

Each signal is converted to a same-date cross-sectional percentile rank. Lower accruals and share
dilution receive better ranks. A row needs at least four available raw fundamental features.

## Models and comparison

Three ridge regressions use the same expanding yearly walk-forward folds and the same
beta-adjusted 21-trading-day target:

1. Frozen price-and-volume features only
2. Fundamental ranks only
3. Price, volume, and fundamental ranks combined

The ridge penalty is 30. The diagnostic portfolio holds the five highest-ranked pilot names,
rebalances monthly, and charges 10 basis points per one-way trade.

## Pass criteria

The fundamentals merit expansion only if the combined model improves the pooled walk-forward
rank IC over the price-only model, the improvement is not confined to one year, feature
coverage is operationally usable, and the result is not driven by a single issuer or sector.
Portfolio returns alone are not a pass condition.

If the pilot passes, the next specification must expand the SEC identity layer and historical
universe before making any portfolio claim.
