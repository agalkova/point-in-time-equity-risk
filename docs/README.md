# Documentation guide

The main [project README](../README.md) gives the shortest overview. The files below preserve the
research decisions, validation results, and engineering details behind that summary.

## Core results

- [S&P 500 out-of-time replication](RESULTS.md)
- [S&P 400 independent replication](SP400_REPLICATION_RESULTS.md)
- [Exuberance hazard model](EXUBERANCE_HAZARD_RESULTS.md)
- [Point-in-time SEC fundamental analysis](POINT_IN_TIME_FUNDAMENTAL_RESULTS.md)
- [Calibrated risk overlay](CALIBRATED_OVERLAY_RESULTS.md)
- [Portfolio engineering](PORTFOLIO_ENGINEERING_RESULTS.md)

## Methodology and data

- [Current research specification](RESEARCH_SPEC.md)
- [Data dictionary](DATA_DICTIONARY.md)
- [Data sources and provenance](DATA_SOURCES.md)
- [Pilot universe](PILOT_UNIVERSE.md)
- [Decision log](DECISIONS.md)

## Operational design

- [Operational drawdown-risk pipeline](PRODUCTION_RISK_PIPELINE.md)
- [Prospective hazard record](PROSPECTIVE_HAZARD_SPEC.md)
- [Prospective operations](PROSPECTIVE_OPERATIONS.md)

The operational pipeline is a local research batch system. It produces monitored signals and
immutable evidence but does not place trades or claim to be a live production service.

## Supporting experiments

- [Advanced model comparison](ADVANCED_RESULTS.md)
- [Expected-return research](ALPHA_RESULTS.md)
- [Fundamental pilot](FUNDAMENTAL_RESULTS.md)
- [SEC archive pilot](SEC_FSDS_PILOT_RESULTS.md)
- [Data-integrity expansion](INTEGRITY_EXPANSION_RESULTS.md)
- [Nasdaq-100 replication status](NDX_REPLICATION_STATUS.md)
- [Hazard challenger](HAZARD_CHALLENGER_RESULTS.md)
- [Fundamental readiness status](FUNDAMENTALS_PILOT_STATUS.md)
- [S&P 400 fundamental transfer plan](SP400_FUNDAMENTAL_TRANSFER_PLAN.md)

## Research history

The versioned specifications show how the project changed without rewriting earlier decisions:

- [Initial specification](RESEARCH_SPEC.md)
- [Exposure-matched portfolio test](RESEARCH_SPEC_V0_2.md)
- [Alpha study](RESEARCH_SPEC_V0_3_ALPHA.md)
- [Prospective specification](PROSPECTIVE_SPEC_V0_4.md)
- [Fundamental pilot](RESEARCH_SPEC_V0_5_FUNDAMENTALS.md)
- [Portfolio engineering](RESEARCH_SPEC_V0_6_PORTFOLIO.md)
- [Nasdaq-100 transfer](RESEARCH_SPEC_V0_7_NDX.md)
- [S&P 400 transfer](RESEARCH_SPEC_V0_8_SP400.md)
- [Exuberance hazard model](RESEARCH_SPEC_V0_9_EXUBERANCE_HAZARD.md)
- [Calibrated overlay](RESEARCH_SPEC_V1_0_CALIBRATED_OVERLAY.md)
- [Hazard challenger](RESEARCH_SPEC_V1_1_HAZARD_CHALLENGER.md)
- [Integrity expansion](RESEARCH_SPEC_V1_2_INTEGRITY_EXPANSION.md)
- [Sector-fundamental extension](RESEARCH_SPEC_V1_3_SECTOR_FUNDAMENTALS.md)

The [project plan](PROJECT_PLAN.md) and [progress log](PROGRESS_LOG.md) retain the chronological work
record. [Resume bullets](RESUME_BULLETS.md) contains concise descriptions for applications and
interviews.
