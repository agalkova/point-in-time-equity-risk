# Prospective alpha record operations

## Purpose

The v0.4 ridge top-50 candidate is the only strategy advancing to prospective observation. The
record begins with the first month-end signal after the 2026-10-22 freeze date.

## Creating a signal record

After the configured Alpaca price panel and point-in-time membership files have been refreshed
through a new month-end, run:

```bash
.venv/bin/python scripts/generate_prospective_alpha_candidate.py
```

For an eligible date, the command creates:

```text
reports/prospective/
├── ledger.csv
└── signals/
    └── YYYY-MM-DD/
        ├── holdings.csv
        ├── manifest.json
        └── ranked_universe.csv
```

Each file is written once. Re-running the same signal is allowed only when its bytes are identical.
Different content for an existing signal date raises an error. SHA-256 hashes in the ledger bind
the ranked universe, holdings, and manifest to the original record.

The manifest records the signal date, training cutoff, market-data cutoff, turnover, modeled cost,
and whether realized performance is still pending. Missing months may not be backfilled silently.

## Current state

The latest available market data ends on 2026-09-30. That signal predates the freeze and remains
a shadow output excluded from prospective evidence. No eligible prospective observation exists
yet. The first eligible record requires a month-end after 2026-10-22.

## Evaluation discipline

Do not revise the model, features, ridge penalty, position count, weighting rule, or transaction
cost while the prospective record is active. Report the first review after 12 eligible monthly
observations, with SPY, the point-in-time equal-weight universe, and six-factor attribution.
