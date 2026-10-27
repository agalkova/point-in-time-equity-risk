# Direct-SEC fundamentals archive pilot

## Decision

The official 2024 Q1 SEC Financial Statement Data Set is accessible through the ordinary SEC
download page even though automated requests from this environment receive HTTP 403. The archive
was parsed successfully without extracting its large text files to disk.

The direct data source is viable, but the proposed universal six-feature schema is not. Only
14 of 30 sector-balanced issuers had all six values, or **46.7%**, below the precommitted 50%
coverage gate. A nonfinancial diagnostic excluding Financials and Real Estate reached **56.0%**,
which confirms that the shortfall is substantially an accounting-schema problem rather than a
download problem. The replacement sector-aware schemas are now frozen, and all three passed the
pilot gate: **56%** for 25 nonfinancial issuers, **100%** for three Financials issuers, and **100%**
for two Real Estate issuers. The two smaller groups still require confirmation on historical data.

## Source and sample

- Official source: [SEC Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)
- Archive tested: 2024 Q1, 118.58 MB
- Eligible current S&P 500 issuers with a 10-K in the archive: 392
- Pilot: 30 unique CIKs selected by deterministic round-robin sampling across all 11 GICS sectors
- Identity key: permanent SEC CIK; ticker and company name are descriptive fields only
- Availability date: actual SEC filing date, never the fiscal-period label

The pipeline reads `sub.txt` and streams `num.txt` in chunks. It rejects co-registrant and
dimensional segment facts, retains source accessions and tags, and uses only annual facts from the
primary financial statements. The archive is never fully extracted, which keeps the design usable
on a machine with limited free disk space.

## Six-feature audit

| Feature | Coverage |
|---|---:|
| Gross margin | 63.3% |
| Operating margin | 66.7% |
| Operating cash flow / revenue | 96.7% |
| Return on average assets | 100.0% |
| Liabilities / assets | 100.0% |
| Asset growth | 100.0% |
| All six simultaneously | 46.7% |

Gross profit is derived from revenue minus cost of revenue when the issuer does not publish a
`GrossProfit` fact. Total liabilities are derived from assets minus stockholders' equity when a
standalone `Liabilities` fact is absent. These are accounting identities, not imputations.

All 30 rows were reviewed for filing timing, missingness, and economic ranges. The automated audit
also recomputed every available ratio from its raw components. It found zero duplicate accessions,
zero arithmetic discrepancies, zero economic-range flags, and zero filings dated before their
fiscal period end. Filing lags ranged from 29 to 72 days, with a 49.5-day median.

Representative raw-fact checks covered ordinary operating companies, utilities, insurers, real
estate, and technology issuers. They confirmed that missing gross and operating margins for banks,
insurers, REITs, and some utilities reflect different statement presentation, while the earlier
implausible ratios came from dimensional segment facts and disappeared after the `segments` filter
was enforced.

The machine-readable evidence is in
`reports/tables/sec_fsds_2024q1_pilot_audit.json`. The normalized pilot remains local under
`data/interim/sec_fsds/` and is excluded from Git.

To reproduce this environment's browser-download route, download `2024 Q1` from the official page
above and run:

```bash
.venv/bin/python scripts/download_sec_fsds_pilot.py \
  --period 2024q1 --archive-path ~/Downloads/2024q1.zip
.venv/bin/python scripts/audit_sec_fsds_pilot.py --period 2024q1
```

The externally supplied archive is read in place and never deleted by the script.

After saving the official SEC `company_tickers.json` registry under `data/raw/sec/`, reproduce the
historical identity audit with:

```bash
.venv/bin/python scripts/build_sec_identity_map.py \
  --fsds-archive ~/Downloads/2024q1.zip
```

This writes the full interval map, the unresolved review queue, and a gate manifest under
`data/interim/sec_identity/`. These local data products are excluded from Git; the construction
code, thresholds, tests, and aggregate results are versioned.

## Frozen next specification and identity gate

Do not fill structurally inapplicable ratios with medians and do not drop entire sectors merely to
raise a headline coverage number. The project now freezes three schemas:

1. Nonfinancial companies use the six tested profitability, cash-flow, leverage, and growth ratios.
2. Financials replace gross and operating margins with net margin, equity/assets,
   cash-flow/assets, and revenue growth.
3. Real Estate uses a cash-flow-oriented variant without gross or operating margin.

After processing all quarters from 2014 Q1 through 2026 Q3, the historical identity layer resolves
699 of 731 membership intervals, representing 98.15% of membership-days and 95.62% of intervals.
The identity gate passes, while the unresolved 32 intervals stay in an explicit review queue. The
complete panel reaches 50.1% nonfinancial, 61.6% Financials, and 82.7% Real Estate complete-case
coverage. All archive-stage gates pass. Full rules are frozen in
`docs/RESEARCH_SPEC_V1_3_SECTOR_FUNDAMENTALS.md`.
