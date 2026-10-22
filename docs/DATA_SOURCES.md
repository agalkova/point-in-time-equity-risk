# Data sources

## Legacy source

The original project contains 502 wide price and volume histories covering 2012-06-13 through 2019-06-12. The provider, price-field definition, constituent snapshot date, and redistribution rights are undocumented. Treat these files as read-only research inputs, not publishable data.

## Alpaca historical market data

Primary endpoint:

- `GET https://data.alpaca.markets/v2/stocks/bars`
- Official reference: https://docs.alpaca.markets/us/reference/stockbars

Required parameters:

- `timeframe=1Day`
- `feed=sip`
- Explicit `start` and `end`
- Explicit `adjustment`
- Pagination until `next_page_token` is empty

The project records both raw and fully adjusted downloads during reconciliation. Raw prices preserve observed bars. Fully adjusted prices may be appropriate for return features, subject to overlap validation.

Alpaca documents `sip` as consolidated US-exchange data and `iex` as a single-exchange feed. IEX-only volume must not be substituted for SIP volume.

Credentials are read from `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`. They must never be written to configuration files, logs, notebooks, or Git history.

## Pilot reconciliation result

The 2016-01-01 through 2019-06-12 pilot requested 20 securities and returned all 20,
including current, renamed, acquired, and delisted names. The audit matched 16,810
security-date observations against the legacy files.

| Check | Result |
|---|---:|
| Median raw daily-return correlation | 0.9994 |
| Minimum raw daily-return correlation | 0.9942 |
| Median fully adjusted daily-return correlation | 1.0000 |
| Minimum fully adjusted daily-return correlation | 0.9999 |
| Median raw close absolute difference vs. legacy | 2.38% |
| Median raw volume correlation | 0.9905 |
| Minimum raw volume correlation | 0.9732 |
| Median Alpaca-to-legacy volume ratio | 1.0814 |

Raw Alpaca close was the closest price-level definition for all 20 securities. Fully
adjusted returns aligned slightly better for dividend-paying names, which is expected and
does not mean the legacy field itself was fully adjusted. Volume levels differ modestly by
vendor, but their time-series agreement is strong enough for normalized volume features.

The pilot supports using Alpaca SIP for the expanded pipeline. It does not establish that
the legacy universe was point-in-time or free of survivorship bias; modern universe design
remains a separate research decision.

