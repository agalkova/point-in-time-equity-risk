# Documentation guide

The main [project README](../README.md) gives the shortest overview. The files below preserve the
research decisions, validation results, and engineering details behind that summary.

## Core results

- [S&P 500 out-of-time replication](RESULTS.md)
- [S&P 400 independent replication](SP400_REPLICATION_RESULTS.md)
- [Point-in-time SEC fundamental analysis](POINT_IN_TIME_FUNDAMENTAL_RESULTS.md)

## Methodology and data

- [Current research specification](RESEARCH_SPEC.md)
- [Data dictionary](DATA_DICTIONARY.md)
- [Data sources and provenance](DATA_SOURCES.md)
- [Pilot universe](PILOT_UNIVERSE.md)
- [Decision log](DECISIONS.md)

## Operational design

- [Operational drawdown-risk pipeline](PRODUCTION_RISK_PIPELINE.md)
- [Prospective hazard record](PROSPECTIVE_HAZARD_SPEC.md)
- [Archived prospective alpha protocol](PROSPECTIVE_OPERATIONS.md)

The operational pipeline is a local research batch system. It produces monitored signals and
immutable evidence but does not place trades or claim to be a live production service.

## Research history

Superseded specifications, scripts, reports, and figures are retained in the
[research archive](../archive/README.md). They document how the work changed, but they are not
current entry points or additional headline claims.
