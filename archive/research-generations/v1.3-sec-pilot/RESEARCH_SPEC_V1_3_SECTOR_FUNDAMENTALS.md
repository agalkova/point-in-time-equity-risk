# v1.3 sector-aware fundamentals expansion

## Purpose and status

This specification freezes the data rules for expanding official SEC fundamentals across the
point-in-time S&P 500 universe. It is a data-engineering milestone, not an alpha claim. The
fundamental model remains disabled until the identity and historical coverage gates below pass.

## Point-in-time identity

The permanent SEC CIK is the issuer key. Tickers and company names are aliases that may change or
be reused. Membership is compressed into ticker intervals, then resolved in this order:

1. current S&P 500 component CIKs for intervals active at the latest membership date;
2. a unique exact ticker in the official SEC company-ticker registry, provided the membership and
   SEC names agree and the ticker has only one membership interval;
3. a filing-name match from an official SEC Financial Statement Data Set archive only when name
   similarity is at least 0.92 and exceeds the runner-up by at least 0.05;
4. otherwise, explicit review. No uncertain identity is silently accepted.

The staged archive download may begin at 90% resolved membership-day coverage. Fundamentals may
not enter a model until at least 95% of membership intervals are resolved. Each newly processed
quarter can contribute historical filing names and reduce the review queue.

## Frozen sector schemas

All values come from annual 10-K or 10-K/A filings. A value becomes available on its actual SEC
filing date. Dimensional segment facts and co-registrant facts are excluded. Ratios are ranked
within sector; a structurally missing ratio is not median-filled.

### Nonfinancial companies

- gross margin
- operating margin
- operating cash flow / revenue
- return on average assets
- liabilities / assets
- annual asset growth

### Financials

- net margin
- return on average assets
- equity / assets
- operating cash flow / average assets
- annual revenue growth
- annual asset growth

### Real Estate

- net margin
- operating cash flow / revenue
- return on average assets
- liabilities / assets
- annual revenue growth
- annual asset growth

Comparative assets and revenue must come from the same filed 10-K, so a growth feature never uses
a later filing. Gross profit may be derived as revenue minus cost of revenue, and liabilities may
be derived as assets minus equity; these accounting identities are recorded rather than treated as
imputation.

The machine-readable definition is `configs/fundamental_schemas_v1.toml`.

## Frozen gates

- Each schema needs at least 50% complete-case issuer coverage before historical modeling.
- Identity needs at least 95% resolved membership-interval coverage before model enablement.
- The price-only benchmark, chronological folds, and modern holdout remain unchanged.
- The combined model must improve pooled out-of-sample rank IC, the improvement cannot be confined
  to one year or one sector, and uncertainty must be reported with paired block resampling.
- Portfolio evidence must use the point-in-time universe, transaction costs, cash-matched exposure,
  and factor-adjusted returns. Failure to beat the benchmark remains a valid result.

## Pilot evidence and next stage

The 2024 Q1 archive pilot produced complete-case coverage of 56% for 25 nonfinancial issuers, 100%
for three Financials issuers, and 100% for two Real Estate issuers. The small Financials and Real
Estate samples establish parsing feasibility, not population coverage.

After processing every quarter from 2014 Q1 through 2026 Q3, 699 of 731 membership intervals are
resolved. They represent 98.15% of membership-days and 95.62% of intervals, clearing the model
identity gate. The complete archive history contains 7,815 filings for 683 issuers with no duplicate
accessions or filing-date violations.

Historical complete-case coverage is 50.1% for nonfinancials, 61.6% for Financials, and 82.7% for
Real Estate. All three frozen coverage gates pass, although the nonfinancial margin is narrow and
must be reported rather than rounded into a stronger claim. The archive stage is complete. Model
work may advance to point-in-time joins, while remaining disabled until join timing, historical
sector treatment, and the known pre-2022 SIVB backfill gap are audited.
