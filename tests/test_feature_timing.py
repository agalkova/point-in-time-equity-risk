import unittest

import numpy as np
import pandas as pd

from risk_managed_momentum.features.build import build_research_dataset


class FeatureTimingTests(unittest.TestCase):
    def test_future_price_changes_do_not_change_signal_date_features(self) -> None:
        dates = pd.bdate_range("2022-01-03", periods=240)
        tickers = [f"S{i:02d}" for i in range(12)]
        base = 100.0 * np.power(1.004, np.arange(len(dates), dtype=float))
        price = pd.DataFrame(
            {ticker: base * (1.0 + index * 0.001) for index, ticker in enumerate(tickers)},
            index=dates,
        )
        day = np.arange(len(dates), dtype=float)
        volume = pd.DataFrame(
            {
                ticker: 1_000_000.0 * (1.0 + 0.10 * np.sin(day / 5.0 + index))
                for index, ticker in enumerate(tickers)
            },
            index=dates,
        )
        config = {
            "eligibility": {"minimum_runup": 0.20, "maximum_distance_below_peak": -0.10},
            "target": {"horizon_days": 40, "drawdown_threshold": -0.15},
        }
        signal_date = dates[160]
        original = build_research_dataset(price, volume, config)

        changed_price = price.copy()
        changed_price.loc[dates[161]:, :] *= 0.50
        changed = build_research_dataset(changed_price, volume, config)

        original_row = original.frame[
            (original.frame["date"] == signal_date) & (original.frame["ticker"] == "S00")
        ].iloc[0]
        changed_row = changed.frame[
            (changed.frame["date"] == signal_date) & (changed.frame["ticker"] == "S00")
        ].iloc[0]
        for column in original.feature_columns:
            self.assertAlmostEqual(original_row[column], changed_row[column], places=12)
        self.assertNotEqual(original_row["future_min_return"], changed_row["future_min_return"])


if __name__ == "__main__":
    unittest.main()

