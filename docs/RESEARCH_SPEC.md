# Research specification

Specification version: 0.1.0  
Frozen on: 2026-10-21

## Primary question

Among US large-cap equities experiencing a substantial recent run-up, can information available on signal date `t` rank the risk of a severe drawdown over the following 40 trading days?

## Eligibility rule

An observation is eligible when:

1. Adjusted price gained at least 20% over the trailing 60 trading days.
2. Adjusted price is no more than 10% below its trailing 60-day maximum.
3. Required feature history exists on the signal date.

## Primary target

The binary event equals one when the minimum adjusted-price return relative to the signal-date price is at or below -15% during trading days `t+1` through `t+40`.

The continuous outcome is maximum forward loss severity over the same interval, floored at zero.

## Permitted primary features

- Trailing returns over 5, 20, 60, and 120 trading days.
- Realized return volatility over 20 and 60 trading days.
- Ratio of short- to medium-horizon volatility.
- Distance from trailing 20- and 60-day highs.
- Trend acceleration based on 20- and 60-day returns.
- Rolling beta and idiosyncratic volatility versus an explicitly documented benchmark.
- Same-day volume surprise and trailing volume trend.
- Trailing dollar-volume liquidity.
- Market return, volatility, breadth, and cross-sectional dispersion available on date `t`.
- Cross-sectional ranks computed only from the eligible point-in-time universe on date `t`.

No feature may use revised fundamentals, future constituent membership, future corporate actions, or a statistic whose window extends beyond date `t`.

## Samples

Legacy development samples:

- Train: 2012-12-01 through 2015-10-30.
- Validation: 2016-03-01 through 2016-10-31.
- Legacy test: 2017-03-01 through 2019-03-15.

Modern replication:

- 2016-01-01 through 2019-06-12 is reserved for source reconciliation.
- 2020-01-01 onward is the modern out-of-time replication period.
- Model or feature changes motivated by modern-period results create a new specification version and a new holdout policy. They may not be described as confirmation of version 0.1.0.

## Primary metrics

1. Daily cross-sectional Spearman rank correlation with forward loss severity.
2. Drawdown-event rate by same-day score decile.
3. Highest-minus-lowest-decile event-rate difference.
4. Highest-to-lowest-decile risk ratio.
5. Average precision and lift over event prevalence.
6. Event-level recall, false-warning rate, and warning lead time.

Use a moving-block bootstrap with a 40-trading-day block for uncertainty on daily statistics.

## Baselines

- 60-day return alone.
- 20-day realized volatility alone.
- 60-day beta alone.
- 60-day idiosyncratic volatility alone.
- A simple equal-weight rank composite fixed before testing.
- Ordinary momentum portfolio without drawdown-risk adjustment.

## Portfolio experiment

The expected-return and drawdown-risk estimates are separate. The portfolio score is a validation-selected combination of expected-return rank and drawdown-risk rank. Tests must include weekly and monthly rebalancing, costs, turnover, maximum position size, sector exposure, and market beta.

## Success criteria

Continued development requires all of the following:

- Positive daily rank correlation in the modern period with a block-bootstrap interval that does not center near zero.
- Positive highest-minus-lowest-decile event-rate spread in most calendar years and major regimes.
- Incremental ranking value versus the best single-factor baseline.
- No evidence that the result depends entirely on survivorship, ticker mapping errors, one sector, or one crisis.

A portfolio claim requires improvement over ordinary momentum after costs on risk-adjusted metrics. Risk-model success alone does not establish alpha.

