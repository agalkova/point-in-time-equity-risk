# SEC fundamentals pilot status

## Completed state — 2026-10-22

The v0.5 proof of concept is complete. The combined model produced a small mean rank-IC lift over
the matched price-only model, but the paired block interval crossed zero, improvement appeared in
only three of five years, and the concentrated portfolio deteriorated. The feature set did not
pass the expansion threshold. Full results are in `docs/FUNDAMENTAL_RESULTS.md`.

The first data retrieval attempt stopped before downloading any issuer because the SEC edge
returned HTTP 403 to this execution environment. A second request to the official bulk archive
received the same response. No unofficial mirror or scraping workaround was used.

The same 403 occurred when the project owner ran the downloader from a normal Terminal. Before
observing model results, a v0.5.1 fallback was added for PtData's open, no-key point-in-time API.
The fallback reports SEC Companyfacts as its upstream source and preserves each metric's source
accession and knowledge timestamp. It is explicitly labeled as a third-party normalization layer.

## Resume commands

Preferred direct-SEC route, on a network that permits `data.sec.gov`:

```bash
export SEC_USER_AGENT="Your Name your-email@example.com"
.venv/bin/python scripts/download_sec_fundamentals.py
.venv/bin/python scripts/run_fundamental_pilot.py
```

The request identity is sent only as an HTTP header and is not written to the repository.

Fallback route, requiring no account or API key:

```bash
.venv/bin/python scripts/download_ptdata_fundamentals.py
.venv/bin/python scripts/run_fundamental_pilot.py
```

## Decision after the run

Expand the pipeline only if the combined model improves pooled out-of-sample rank IC over the
price-only pilot, improvement is not isolated to one year, and the coverage audit shows that the
signals are usable across issuers. Do not promote the pilot portfolio return as alpha because the
small universe begins from current constituents.
