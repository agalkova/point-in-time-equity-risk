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

The source is the SEC Companyfacts API. Only annual USD observations from forms 10-K and
10-K/A are retained. A value becomes available on its `filed` date, never at its fiscal period
end. At each month-end signal, the pipeline performs a backward as-of join to the latest filing
known on that date. Automated tests fail if a post-signal filing enters a feature row.

Annual comparative facts repeated in later filings are excluded by requiring the financial
period end to be no more than 150 days before the filing date. Flow facts must span 250–450
days. XBRL tag aliases are ordered and deterministic.

## Signals

- Return on assets
- Gross profit divided by assets
- Operating income divided by assets
- Operating cash flow divided by assets
- Accruals: net income minus operating cash flow, divided by assets
- Liabilities divided by assets
- Annual revenue growth
- Annual asset growth

Each signal is converted to a same-date cross-sectional percentile rank. Lower accruals,
leverage, and asset growth receive better ranks. A row needs at least four available raw
fundamental features.

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
