# Pilot universe

The first download uses 20 names selected to expose ordinary and difficult data cases before scaling to all legacy securities.

## Ordinary active cases

- AAPL
- MSFT
- JPM
- XOM
- NVDA
- WMT
- AMZN
- CAT
- GOOGL

These names test normal coverage, price adjustments, trading calendars, and consolidated volume.

## Rename case

- META, corresponding to legacy ticker FB

This tests Alpaca's historical `asof` symbol mapping. The mapping must be recorded rather than silently replacing the legacy identifier.

## Acquired, inactive, or structurally complex legacy cases

- XLNX
- CELG
- MON
- ESRX
- RHT
- AET
- CBS
- VIAB
- WYN
- LLL

These names test missing-symbol behavior, final trading dates, mergers, ticker reuse, and the rule that prices must not be forward-filled after a security stops trading.

The expected corporate-action mapping for each difficult case will be researched and recorded only after observing the provider response. The pipeline must not infer that an acquirer is the same security as the acquired company.

