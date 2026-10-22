# Risk-Managed Momentum

Research and engineering project for forecasting severe drawdowns after strong equity price run-ups.

## Research question

Among stocks that gained at least 20% over the previous 60 trading days and remain within 10% of their trailing high, can information available on the signal date rank the risk of a severe loss during the next 40 trading days?

The project combines three deliverables:

1. A point-in-time equity data pipeline.
2. A leakage-controlled cross-sectional drawdown-risk model.
3. A transaction-cost-aware risk-managed momentum portfolio experiment.

## Current evidence

The legacy 2012–2019 feasibility test supports continued research, with limitations:

- Highest-risk-decile drawdown-event rate: 15.5%.
- Lowest-risk-decile drawdown-event rate: 3.1%.
- Top-to-bottom risk ratio: 5.1 times.
- Mean daily rank correlation with future drawdown severity: 0.196.
- Test ROC AUC: 0.569.
- A naïve daily portfolio overlay did not improve return or maximum drawdown.

The defensible result is cross-sectional risk ranking. The project does not currently claim to predict bubbles or produce alpha.

## Repository structure

```text
configs/                  Frozen research and data settings
data/                     Local data layers; contents are excluded from Git
docs/                     Specification, decisions, progress, and data definitions
reports/                  Generated tables and figures
scripts/                  Command-line entry points
src/risk_managed_momentum Reusable pipeline and research code
tests/                    Timing, target, and data-contract tests
```

## Quick start

Create an environment and install the project:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

Run the legacy source audit:

```bash
python scripts/audit_legacy_data.py
```

Reproduce the frozen legacy feasibility result:

```bash
python scripts/run_legacy_feasibility.py
```

Create a private `.env` file in the project root (it is excluded from Git):

```text
APCA_API_KEY_ID=...
APCA_API_SECRET_KEY=...
```

Then run a download:

```bash
python scripts/download_alpaca.py --symbols-file data/reference/pilot_symbols.txt \
  --start 2016-01-01 --end 2019-06-12
```

The downloader explicitly requests the `sip` feed. It refuses to continue if the response cannot be identified as the requested historical source.

After downloading both `raw` and `all` adjustment variants for the reconciliation period:

```bash
python scripts/reconcile_overlap.py \
  --raw-bars data/raw/alpaca/bars_2016-01-01_2019-06-12_raw.csv.gz \
  --adjusted-bars data/raw/alpaca/bars_2016-01-01_2019-06-12_all.csv.gz
```

The audit compares price levels, daily returns, consolidated volume, coverage dates, and symbol mappings for each pilot security.

The completed pilot retrieved 16,810 overlapping observations across all 20 requested
securities, including renamed and delisted names. Results support raw close as the closest
match to the legacy price level, while adjusted returns are retained as a candidate for
economically meaningful return features. See `docs/DATA_SOURCES.md` for the reconciliation
summary and limitations.

## Research controls

The primary eligibility rule, outcome, time splits, metrics, and modern holdout policy are defined in [docs/RESEARCH_SPEC.md](docs/RESEARCH_SPEC.md). Any change must be recorded in [docs/DECISIONS.md](docs/DECISIONS.md) before the modern holdout is evaluated.

Raw vendor data and API credentials must never be committed. The public repository will include reproducible download code, schemas, validation summaries, and a small redistribution-safe example dataset.

## Status

See [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md) for completed work and the next action.

