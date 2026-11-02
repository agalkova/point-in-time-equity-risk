# Archived prospective alpha plan

## Status

Archived on 2026-11-01 before the first eligible post-freeze observation. No prospective result is
claimed. The code and protocol remain as a record of how the experiment would have been operated,
but this repository does not maintain an active monthly track record.

## Purpose

The v0.4 ridge top-50 candidate was selected for a possible prospective observation period. The
planned record would have begun with the first month-end signal after the 2026-10-22 freeze date.

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

## State at archival

The available operating data ended on 2026-09-30. That signal predates the freeze and remains a
shadow output excluded from prospective evidence. No eligible prospective observation was added to
the record before it was archived.

## Evaluation discipline

If this experiment is restarted, it requires a new dated specification. The model, features, ridge
penalty, position count, weighting rule, transaction cost, and review schedule must be fixed before
the first new observation is recorded.
