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

Current interpretation:

- The signal is promising as a cross-sectional risk ranker.
- The signal is not yet a profitable trading strategy.
- The next major evidentiary step is source reconciliation followed by a modern untouched replication.

Next actions:

1. Obtain Alpaca API credentials locally.
2. Download raw and adjusted SIP bars for the 20-security pilot over 2016–2019.
3. Produce the overlap and ticker-history audit.
4. Confirm price adjustment and consolidated-volume compatibility.
5. Expand the download only after the pilot passes.

