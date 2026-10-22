# Data dictionary

## Canonical daily-bar fields

| Field | Type | Definition |
|---|---|---|
| `date` | date | New York trading-session date. |
| `security_id` | string | Stable internal identifier independent of ticker changes. |
| `ticker` | string | Symbol used for the record after documented mapping policy. |
| `requested_ticker` | string | Symbol submitted to the provider. |
| `open` | float | Session opening price under the recorded adjustment policy. |
| `high` | float | Session high under the recorded adjustment policy. |
| `low` | float | Session low under the recorded adjustment policy. |
| `close` | float | Session closing price under the recorded adjustment policy. |
| `volume` | integer | Eligible consolidated share volume for the selected feed. |
| `trade_count` | integer | Number of eligible trades included in the provider bar. |
| `vwap` | float | Provider volume-weighted average price. |
| `feed` | string | Market-data feed; primary value is `sip`. |
| `adjustment` | string | Corporate-action adjustment requested from the provider. |
| `source` | string | Data provider name. |
| `retrieved_at_utc` | timestamp | Retrieval timestamp for lineage. |

## Model fields

| Field | Type | Definition |
|---|---|---|
| `eligible` | boolean | Meets the frozen trailing run-up and near-peak conditions. |
| `future_min_return_40` | float | Minimum return from signal price during the next 40 trading days. |
| `drawdown_event_40_15` | boolean | `future_min_return_40 <= -0.15`. |
| `drawdown_severity_40` | float | Maximum loss magnitude over 40 days, floored at zero. |
| `risk_score` | float | Model score trained only on earlier samples. |
| `risk_decile` | integer | Same-day cross-sectional score decile from 1 to 10. |

