from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-02", periods=180)
    rows = []
    for index in range(12):
        ticker = f"SYN{index + 1:02d}"
        shocks = rng.normal(0.0005 + index * 0.00003, 0.012 + index * 0.0002, len(dates))
        close = 50.0 * np.exp(np.cumsum(shocks))
        overnight = rng.normal(0.0, 0.002, len(dates))
        open_price = close * np.exp(overnight)
        spread = np.abs(rng.normal(0.006, 0.002, len(dates)))
        high = np.maximum(open_price, close) * (1.0 + spread)
        low = np.minimum(open_price, close) * (1.0 - spread)
        volume = rng.lognormal(13.5 + index * 0.02, 0.25, len(dates)).round()
        for day, open_value, high_value, low_value, close_value, volume_value in zip(
            dates, open_price, high, low, close, volume, strict=True
        ):
            rows.append(
                {
                    "date": day.date(),
                    "ticker": ticker,
                    "open": round(float(open_value), 4),
                    "high": round(float(high_value), 4),
                    "low": round(float(low_value), 4),
                    "close": round(float(close_value), 4),
                    "volume": int(volume_value),
                    "source": "synthetic",
                }
            )
    output = PROJECT_ROOT / "data" / "example" / "synthetic_bars.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Saved {len(rows):,} synthetic rows to {output}")


if __name__ == "__main__":
    main()
