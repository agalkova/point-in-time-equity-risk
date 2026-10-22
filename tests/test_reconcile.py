import unittest

import pandas as pd

from risk_managed_momentum.data.reconcile import reconcile_legacy_overlap


class ReconciliationTests(unittest.TestCase):
    def test_identical_series_are_identified_as_compatible(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=5)
        legacy_price = pd.DataFrame({"AAA": [10.0, 10.5, 11.0, 10.8, 11.2]}, index=dates)
        legacy_volume = pd.DataFrame({"AAA": [100, 110, 120, 105, 130]}, index=dates)
        bars = pd.DataFrame(
            {
                "date": dates,
                "ticker": "AAA",
                "close": legacy_price["AAA"].to_numpy(),
                "volume": legacy_volume["AAA"].to_numpy(),
            }
        )
        detail, summary = reconcile_legacy_overlap(
            legacy_price,
            legacy_volume,
            raw_bars=bars,
            adjusted_bars=bars,
            provider_to_legacy={"AAA": "AAA"},
        )
        self.assertEqual(len(detail), 5)
        self.assertAlmostEqual(summary.iloc[0]["raw_return_correlation"], 1.0)
        self.assertAlmostEqual(summary.iloc[0]["raw_median_volume_ratio"], 1.0)
        self.assertAlmostEqual(summary.iloc[0]["raw_median_absolute_return_difference"], 0.0)


if __name__ == "__main__":
    unittest.main()

