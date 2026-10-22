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

Current interpretation:

- The signal is promising as a cross-sectional risk ranker.
- The signal is not yet a profitable trading strategy.
- The source reconciliation passed; the next major evidentiary step is a controlled data expansion followed by the untouched modern replication.

Next actions:

1. Freeze the modern-universe construction and survivorship-bias policy.
2. Download the broader research universe without inspecting modern model outcomes.
3. Build and validate the point-in-time feature table.
4. Run the frozen specification once on the 2020 onward replication period.
5. Report both ranking performance and the transaction-cost-aware portfolio result, including failures.

