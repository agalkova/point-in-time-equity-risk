# Integrity repair and expanded hazard study (v1.2)

## Outcome

This iteration made the experiment more credible, but it did not manufacture a new winning model.
The main deliverable is a corrected research system with explicit corporate-action valuation,
post-index-exit prices, a longer point-in-time panel, paired model inference, and a frozen forward
record.

## Data integrity result

- Expanded S&P 500 panel: 2016-01-04 through 2026-10-23, 723 historical symbols.
- Mean in-membership price coverage: 99.96%; median coverage: 100%.
- Mature exuberance episodes audited: 6,138.
- Previously incomplete mature paths repaired: 26.
- Unresolved mature paths after repair: 0.
- Recent episodes correctly retained as not yet mature: 148.

Membership now controls signal eligibility without erasing a security's later prices. Cash,
stock, and mixed mergers are valued through documented consideration; ticker reuse and renames
are dated explicitly. Portfolio engines now fail closed if a held security lacks a return instead
of treating that absence as a zero return.

## Frozen model comparison

Three candidates were fit through 2024 and selected only on 2025. The rolling model trained from
2022 won the declared 2025 criterion with 0.648 ROC AUC and 1.751x average-precision lift on 516
episodes.

On 403 mature 2026 episodes:

| Model | ROC AUC | AP lift | Brier score | Top/bottom risk ratio |
|---|---:|---:|---:|---:|
| Active legacy champion | 0.707 | 1.745x | 0.158 | 6.40x |
| Selected rolling-2022 candidate | 0.700 | 1.767x | 0.153 | 7.75x |

The paired 60-date block bootstrap did not establish an overall improvement:

- ROC AUC difference: -0.0195, 95% interval [-0.0361, -0.0029].
- Average-precision-lift difference: +0.0214, 95% interval [-0.0535, +0.1408].

The candidate modestly improved precision lift and calibration but lost ranking AUC. Because the
interval for precision includes zero, and because 2026 was already inspected in earlier work, the
candidate remains research-only. No model pointer was changed.

## Fundamental coverage gate

The intended six-feature filing-date ablation was not fit. The free point-in-time pilot covers
22 of 723 historical symbols (3.0%) and only 40 of 6,138 episodes (0.65%) even for the three
available duration features. Return on assets, liabilities/assets, and asset growth are absent.
The official SEC Companyfacts endpoint continues to return HTTP 403 from this environment.

Fitting on the available sample would turn the experiment into a current-survivor study. The
automated gate therefore records `do_not_fit_biased_fundamental_model`. This is a valid negative
engineering result, not a missing backtest.

## Prospective confirmation

The forward record begins on 2026-10-27. It pins the exact active and shadow artifact IDs, copies
each daily challenger prediction into immutable evidence, verifies source hashes, and never
rewrites prior predictions. A separate daily maturation step attaches 10/20/40/60-day outcomes
only after all required future prices exist. Review requires both 12 calendar months and 250
mature episodes.

## Reproduction

```bash
python scripts/audit_data_integrity.py
python scripts/run_integrity_expanded_hazard.py
python scripts/audit_fundamental_readiness.py
python scripts/update_hazard_prospective_record.py
python scripts/mature_hazard_prospective_outcomes.py
```

Generated audit tables, predictions, paired intervals, coefficients, and readiness summaries are
written under `reports/tables/`; licensed or derived datasets remain excluded from Git.
