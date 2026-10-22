# Nasdaq-100 replication status

## 2026-10-22

The v0.7 cross-universe specification and complete reproducible pipeline were frozen before model
evaluation. Thirty-three repository tests pass.

The free point-in-time membership service reached its 200-request daily IP quota after six NDX
month-end snapshots were cached. The downloader is resumable and does not repeat completed dates.
No Nasdaq-100 price panel has been downloaded and no model result has been observed.

Resume from the repository root:

```bash
.venv/bin/python scripts/download_ndx_membership.py
.venv/bin/python scripts/download_ndx_alpaca.py
.venv/bin/python scripts/run_ndx_replication.py
```

If the first command reports the daily quota again, rerun after the next UTC quota reset or from a
separate normal network. Do not reduce the snapshot count after the freeze merely to fit the quota.
