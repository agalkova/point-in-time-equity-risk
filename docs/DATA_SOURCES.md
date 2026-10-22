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

