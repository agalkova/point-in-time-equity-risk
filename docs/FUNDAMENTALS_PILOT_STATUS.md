# SEC fundamentals pilot status

## Current state — 2026-10-22

The v0.5 proof-of-concept pipeline is implemented and its local timing/data-contract tests
pass. It covers deterministic pilot selection, polite SEC downloads, raw-response retention,
annual XBRL normalization, filing-date as-of joins, fundamental feature construction, expanding
walk-forward comparison, cost-aware portfolios, and factor attribution.

The first data retrieval attempt stopped before downloading any issuer because the SEC edge
returned HTTP 403 to this execution environment. A second request to the official bulk archive
received the same response. No unofficial mirror or scraping workaround was used.

This is an access blocker, not a completed empirical result. No claim about the value of the
fundamental features should be made until the official data download and walk-forward run finish.

## Resume commands

From the repository root, on a network that permits `data.sec.gov`:

```bash
export SEC_USER_AGENT="Your Name your-email@example.com"
.venv/bin/python scripts/download_sec_fundamentals.py
.venv/bin/python scripts/run_fundamental_pilot.py
```

The request identity is sent only as an HTTP header and is not written to the repository.

## Decision after the run

Expand the pipeline only if the combined model improves pooled out-of-sample rank IC over the
price-only pilot, improvement is not isolated to one year, and the coverage audit shows that the
signals are usable across issuers. Do not promote the pilot portfolio return as alpha because the
small universe begins from current constituents.
