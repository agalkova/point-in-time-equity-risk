# Research specification v0.3: exploratory alpha study

Status: frozen before execution
Created: 2026-10-22
Parent: v0.2 exploratory drawdown-risk research

## Purpose

Test whether the existing point-in-time data system can support a distinct expected-return
signal. This study does not redefine drawdown prediction as alpha. It builds a separate
return target, model comparison, portfolio simulation, and factor-attribution layer.

The 2020–2026 market history has already been observed. All v0.3 findings are exploratory.
Confirmation requires prospective observations collected after this specification or an
independent frozen dataset.

## Universe and signal frequency

- Point-in-time S&P 500 membership reconstructed by the existing pipeline.
- Month-end signals only.
- Adjusted close of at least $5 on the signal date.
- Trailing 20-day average dollar volume of at least $5 million.
- No requirement that a stock first experience a 20% run-up.

## Primary target

The target is the stock's next-21-trading-day return minus its signal-date 126-day beta
multiplied by the equal-weight point-in-time market's next-21-day return. This beta-adjusted
future return is a practical residual-return target built solely from the available price
panel. The beta is estimated using information available at the signal close.

## Candidate signals fixed before execution

- 12-to-1, 6-to-1, and 3-to-1-month momentum;
- one-month return and momentum acceleration;
- beta-adjusted residual momentum;
- volatility, idiosyncratic volatility, skewness, and trailing drawdown;
- volume surprise, volume trend, dollar volume, and Amihud-style illiquidity;
- market return, volatility, breadth, and cross-sectional dispersion.

Security-level signals enter as same-date cross-sectional percentile ranks.

## Fixed models

1. Ridge regression with `alpha=100`.
2. Histogram gradient-boosting regression with the parameters recorded in
   `configs/research_v0_3_alpha.toml`.
3. A fixed 50/50 ensemble after converting both predictions to same-date percentile ranks.
4. A transparent momentum composite: 40% 12-to-1 momentum, 30% 6-to-1 momentum,
   20% 3-to-1 momentum, and 10% contrarian one-month return.

No model or parameter is selected using a test year.

## Validation

- Expanding calendar-year walk-forward tests from 2021 through 2026.
- One complete month-end signal is purged from the end of each training sample, covering
  the 21-trading-day target horizon.
- Primary predictive metrics: mean monthly cross-sectional rank IC and highest-minus-lowest
  decile future residual-return spread.
- Moving-block bootstrap confidence interval over monthly rank IC observations.

## Portfolio tests

All portfolios rebalance monthly and charge 10 basis points one way.

- Primary: long-only, equal-weight top 50 ensemble-ranked stocks.
- Baselines: SPY buy-and-hold, equal-weight point-in-time universe, and the transparent
  momentum composite.
- Secondary: beta-aware long-short research portfolio, long the top 50 and short the bottom
  50 at 50% gross exposure on each side.
- Secondary drawdown overlay: subtract 0.25 times the existing transparent drawdown-risk
  composite from the ensemble's same-day alpha rank.

Report return, volatility, Sharpe ratio, maximum drawdown, turnover, transaction costs,
market beta, and Fama–French factor-adjusted alpha where free factor data are available.

## Success standard

Evidence for candidate alpha requires all of the following:

1. Positive pooled rank IC with a block-bootstrap interval above zero.
2. Positive top-minus-bottom residual-return spread.
3. Positive after-cost portfolio performance relative to the appropriate baseline.
4. Positive factor-adjusted intercept that is not driven by one calendar year.
5. No material leakage, survivorship, timing, or transaction-cost failure.

Failure on these criteria is a valid result and must not be relabeled as alpha.
