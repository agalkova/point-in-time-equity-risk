# Synthetic example data

`synthetic_bars.csv` contains deterministic, simulated OHLCV data for 12 fictional securities.
It includes artificial run-up and drawdown episodes so the public demonstration exercises both
target classes. It exists only to demonstrate schemas, feature construction, chronological
splitting, and model execution without redistributing vendor data. Its metrics are not research
evidence and must not be interpreted as market behavior.

Regenerate it with:

```bash
python scripts/generate_example_data.py
python scripts/run_example_pipeline.py
```
