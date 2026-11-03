# Code map

The repository records several studies, but the main result follows one code path. Start there before reading the later experiments.

## Primary S&P 500 study

[`scripts/run_modern_replication.py`](../scripts/run_modern_replication.py) coordinates the primary evaluation:

1. Load the frozen dates, feature rules, and model settings from [`configs/research.toml`](../configs/research.toml).
2. Load the legacy development data with [`data/legacy.py`](../src/risk_managed_momentum/data/legacy.py).
3. Build trailing features and forward drawdown targets with [`features/build.py`](../src/risk_managed_momentum/features/build.py).
4. Select the logistic-regression setting on the legacy validation period with [`models/drawdown.py`](../src/risk_managed_momentum/models/drawdown.py).
5. Refit that frozen model on all legacy development rows.
6. Build the later point-in-time S&P 500 panel with [`data/panel.py`](../src/risk_managed_momentum/data/panel.py), then apply the same feature definitions.
7. Score the untouched 2020–2026 observations and calculate classification, rank, decile, and block-bootstrap results with [`evaluation/ranking.py`](../src/risk_managed_momentum/evaluation/ranking.py).

The model is ordinary logistic regression. Most of the project is concerned with constructing the correct historical rows and enforcing the date boundary, not with a complicated estimator.

## Independent transfer test

[`scripts/run_sp400_replication.py`](../scripts/run_sp400_replication.py) applies the unchanged model and target to reconstructed S&P 400 membership. It does not retune the estimator. [`data/sp400.py`](../src/risk_managed_momentum/data/sp400.py) contains the universe-specific membership handling; the shared feature and evaluation modules remain the same.

## Supporting modules

| Area | Purpose |
| --- | --- |
| `data/` | Reconstruct dated membership, identifiers, market panels, and SEC filing availability |
| `features/` | Convert point-in-time panels into trailing predictors and strictly forward outcomes |
| `models/` | Fit the frozen logistic model and later research candidates |
| `evaluation/` | Calculate ranking, classification, uncertainty, and portfolio diagnostics |
| `operations/` | Store model artifacts and demonstrate repeatable scoring and monitoring |

## Later research extensions

The alpha, hazard, SEC-fundamental, Nasdaq-100, portfolio-engineering, and operational scripts extend the primary study. They support the additional result documents but are not required to understand the central S&P 500 and S&P 400 claim. Their frozen specifications are retained as a research record.

For a first reading, the seven numbered steps above are the complete path from historical inputs to the headline risk-separation result.
