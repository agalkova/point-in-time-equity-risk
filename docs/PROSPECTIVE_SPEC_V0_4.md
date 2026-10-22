# Prospective alpha-candidate specification v0.4

Status: frozen for future observation
Created: 2026-10-22
Earliest eligible prospective signal: first month-end after 2026-10-22

## Candidate

- Point-in-time S&P 500 universe.
- Month-end rebalance.
- The 22 features and beta-adjusted 21-day target defined in v0.3.
- Ridge regression with fixed `alpha=100`.
- Train on all labeled observations available before each signal.
- Long-only top 50 stocks, equal-weighted at 2% each.
- Adjusted-close return convention and 10 basis points one-way transaction cost.
- No parameter, feature, position count, or cost assumption may be changed while this
  prospective record is active.

## Required record

For every month-end signal, save the as-of date, training cutoff, ranked eligible universe,
selected holdings, target weights, turnover, modeled cost, and subsequent realized return.
Missing or delayed runs remain in the record; they may not be silently removed.

## Evaluation

Report performance after at least 12 monthly observations, while recognizing that stronger
statistical evidence will require substantially more history. Compare with SPY, the
point-in-time equal-weight universe, and the six Fama–French-plus-momentum factors.

The historical v0.3 estimate must remain labeled post-specification. Only observations after
this freeze date contribute to the prospective claim.
