# Decision log

| ID | Date | Decision | Reason | Revisit when |
|---|---|---|---|---|
| D001 | 2026-10-21 | Frame the project as forward drawdown-risk research after momentum run-ups. | The original hindsight bubble labels cannot support a defensible prediction claim. | Only if a separately defined bubble proxy has independent evidence. |
| D002 | 2026-10-21 | Use a 20% trailing 60-day run-up and a 15% loss within 40 trading days as the primary setup. | It provides an interpretable conditional risk problem and adequate event prevalence in the legacy sample. | After the modern holdout is reported, under a new specification. |
| D003 | 2026-10-21 | Separate expected return from drawdown risk. | The feasibility model ranked downside but the naïve exclusion portfolio failed. Low predicted risk is not the same as high expected return. | Never combine them implicitly. |
| D004 | 2026-10-21 | Use Alpaca historical SIP bars for the modern pipeline. | SIP consolidates all US exchanges; IEX-only volume is unsuitable for volume features. | If licensing, coverage, or reconciliation fails. |
| D005 | 2026-10-21 | Preserve 2020 onward as the modern replication sample. | Recent regimes provide the most credible out-of-time test. | A specification change after first reporting requires a new holdout. |
| D006 | 2026-10-21 | Keep vendor data and credentials out of Git. | Market-data rights and secret management require reproducible code without redistribution of restricted raw data. | Only for a clearly redistribution-safe sample. |

