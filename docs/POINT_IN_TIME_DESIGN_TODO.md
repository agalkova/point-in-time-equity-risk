# Point-in-time design note — TODO

This note is intentionally incomplete. Answer the questions below in your own words before treating
it as project documentation.

## Identity resolution

- What identifier represents a company through ticker and name changes?
- Which source establishes the link between a market-data symbol and that identifier?
- What evidence is required before an automatic match is accepted?
- What happens when two plausible matches remain?

## Filing timing

- At what exact date or timestamp does a filing become available to the model?
- How are amended filings handled without changing earlier point-in-time results?
- Which fiscal period, filing, and acceptance dates must be retained for an audit?
- How should multiple eligible filings on the same date be ordered?

## Ticker reuse

- How does the system distinguish a renamed company from a reused ticker?
- What date-bounded evidence prevents observations from two issuers being joined together?
- Which cases require manual review instead of an inferred mapping?

## Unavailable-data boundary

- Which historical facts can the public sources reconstruct, and from what date?
- Which missing values mean “not yet public,” “not reported,” or “not recoverable”?
- When should a row remain missing rather than be filled or inferred?
- Which conclusions must be narrowed because the required historical data is unavailable?
