# Frozen prospective hazard record

The record begins with market data dated 2026-10-27 or later. It compares the already registered
active champion and modern shadow challenger; it does not refit either model.

Every accepted operation run must match the exact model artifact IDs in
`configs/prospective_hazard_v1.toml`. The updater verifies the source manifest and signal hashes,
then creates an immutable dated prediction directory and an append-only ledger entry. Historical
replays dated before the freeze are excluded.

Outcomes are written separately after 60 subsequent trading days are available. Missing price
paths stay pending rather than becoming zero returns. The formal review occurs only after at least
12 calendar months and 250 mature episodes. Any model change starts a new record version.
