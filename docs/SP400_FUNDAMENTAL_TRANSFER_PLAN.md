# S&P 400 fundamental transfer plan

## Status

Preregistered and not run.

The v1.4 S&P 500 analysis identified combined ridge as a prospective candidate after results were
reviewed. It is therefore not confirmatory evidence on the S&P 500 sample. The next valid test is an
unchanged application to securities outside that development universe.

The existing S&P 400 price and point-in-time membership panels are suitable for this purpose. The
compact SEC history is not: it was intentionally filtered to S&P 500 issuer CIKs while processing
the quarterly archives. Most S&P 400 issuers are consequently absent. The transfer test remains
blocked until the SEC archives are reprocessed for an independently resolved S&P 400 CIK set.

## Frozen design

- Candidate: combined price-and-fundamental ridge model with alpha 100
- Target: 21-trading-day beta-adjusted future return
- Training: for each test year, S&P 500 observations from earlier signal dates only
- Evaluation: S&P 400 observations in the held-out year, with no fitting on S&P 400 outcomes
- Identity: permanent SEC CIK within the applicable membership interval
- Filing availability: actual SEC filing date; annual statements expire after 550 days
- Normalization: same-date ranks within the three frozen accounting schemas
- Portfolio diagnostic: top-50/bottom-50, market-neutral, 10 basis points one-way cost

The test passes only if data coverage clears its gates, mean monthly rank IC is positive, at least
four of six years and two of three accounting schemas are positive, the top-minus-bottom residual
return is positive, and the long-short portfolio remains positive after costs.

## Required data work

1. Build S&P 400 membership intervals and resolve them to CIKs without using return outcomes.
2. Audit ticker reuse and retain unresolved intervals in a review queue.
3. Reprocess the 2014 Q1–2026 Q3 SEC archives for the expanded CIK set.
4. Measure identity and filing coverage before generating model predictions.
5. Stop if either coverage gate fails; do not narrow the universe after viewing returns.

The machine-readable specification is
`configs/research_v1_5_sp400_fundamental_transfer.toml`.
