# Progress log

## 2026-10-21

Completed:

- Audited the original notebooks and datasets without modifying them.
- Replaced hindsight bubble membership with a forward 40-day drawdown target.
- Ran a chronological train, validation, and legacy-test feasibility study.
- Added factor comparisons, alternate target definitions, annual stability checks, and a 40-day moving-block bootstrap.
- Rejected an immediate alpha claim after a naïve daily exclusion portfolio failed.
- Created this separate project with a frozen specification and decision log.
- Added the first Alpaca historical SIP client and data-audit foundation.
- Reproduced the recorded feasibility metrics exactly from the modular package.
- Added 13 passing tests covering target timing, sample isolation, legacy data contracts, response normalization, reconciliation, and refusal of IEX data.
- Added raw-versus-adjusted overlap reconciliation for price levels, returns, consolidated volume, coverage dates, and ticker mappings.
- Downloaded raw and fully adjusted Alpaca SIP pilot data for 20 securities over 2016-01-01 through 2019-06-12.
- Reconciled 16,810 overlapping security-date records with no missing requested symbols, including renamed and delisted names.
- Confirmed that raw Alpaca closes are the closest level match to the legacy price field for all 20 pilot securities.
- Confirmed strong provider agreement: median raw-return correlation 0.9994, median adjusted-return correlation 1.0000, and median raw-volume correlation 0.9905.
- Added automatic loading of the private, Git-ignored project `.env` file for downloads.
- Reconstructed 2019–2026 point-in-time S&P 500 membership from 412 public constituent changes.
- Downloaded 1,101,390 adjusted Alpaca SIP bars for 642 returned symbols and a separate SPY benchmark.
- Added dated corporate-action chains and historical `asof` requests, including protection against an unrelated reuse of ticker `STI`.
- Opened the frozen modern holdout once: 91,299 observations, 0.671 ROC AUC, 1.73× average-precision lift, and 18.84 percentage points of top-minus-bottom decile separation.
- Confirmed positive risk separation in every modern calendar year.
- Completed weekly and monthly cost-aware portfolio tests. The return optimizer selected no risk penalty; the monthly exclusion overlay reduced risk but also return and exposure.
- Added 18 passing tests, CI, publication figures, a results report, and resume bullets.

Current interpretation:

- The signal replicated as a cross-sectional risk ranker.
- The multivariate model improves AP and ROC AUC, but a fixed composite is competitive on ranking metrics.
- The signal is not a standalone alpha strategy; its plausible use is as a defensive overlay.
- The project is ready for GitHub review after a final secrets and reproducibility audit.

Next actions:

1. Run the final secrets, repository-size, and clean-clone audit.
2. Optionally add licensed point-in-time sector data; do not infer historical sectors from current labels.
3. Create the GitHub remote only when authorized by the project owner.

