# SEC fundamentals pilot status

## Direct archive follow-up — 2026-10-27

The HTTP 403 did not make official SEC bulk data unusable. The 2024 Q1 Financial Statement Data
Set was downloaded from the ordinary SEC data page and parsed locally with a streaming reader.
A 30-issuer, 11-sector pilot validated permanent-CIK matching, actual filing dates, source tags,
and six accounting features.

Individual feature coverage was 63.3%–100%, but only 46.7% of issuers had all six features. The
universal schema therefore failed the frozen 50% coverage gate. Three sector-aware schemas are now
frozen. Pilot complete-case coverage is 56% for nonfinancials and 100% for the small Financials and
Real Estate samples.

After processing all 51 quarters from 2014 Q1 through 2026 Q3, the historical ticker-to-CIK layer
resolves 699 of 731 membership intervals and 98.15% of membership-days. Interval coverage is
95.62%, clearing the frozen identity gate. The remaining 32 intervals are retained for review; they
are not silently matched. Complete-case coverage is 50.1%, 61.6%, and 82.7% across the three
schemas, so all archive-stage gates pass. At that stage, the model remained disabled pending the
point-in-time join and sector-treatment audits. See `docs/SEC_FSDS_PILOT_RESULTS.md` and
`docs/RESEARCH_SPEC_V1_3_SECTOR_FUNDAMENTALS.md`.

## Expanded point-in-time result — 2026-10-27

The join and sector-treatment audits are complete. Permanent-CIK interval matching and actual
filing-date as-of joins produced 98.33% identity coverage, 97.37% fresh-filing coverage, and zero
future-filing leaks across 41,240 stock-month observations. Historical GICS is not available for
former constituents, so ratios are ranked within frozen accounting schemas and are not described
as historically sector-neutral.

The frozen 2021–2026 comparison found a +0.0056 mean monthly rank-IC improvement for the combined
ensemble, but its paired block interval crossed zero and only three of six years were positive.
The combined long-only portfolio improved annual return from 10.52% to 13.16%, but with higher risk
and an insignificant 1.66% six-factor alpha estimate. Post-specification long-short diagnostics
lost money after costs. The expanded data is accepted as a strong engineering and research result;
the alpha claim is rejected. See `docs/POINT_IN_TIME_FUNDAMENTAL_RESULTS.md`.

## Completed state — 2026-10-22

The v0.5 proof of concept is complete. The combined model produced a small mean rank-IC lift over
the matched price-only model, but the paired block interval crossed zero, improvement appeared in
only three of five years, and the concentrated portfolio deteriorated. The feature set did not
pass the expansion threshold. Full results are in `docs/FUNDAMENTAL_RESULTS.md`.

The first API data retrieval attempt stopped before downloading any issuer because the SEC edge
returned HTTP 403 to this execution environment. A second request to the official bulk archive
received the same response. The later direct-archive pilot used the official SEC download page;
no unofficial mirror or scraping workaround was used.

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
