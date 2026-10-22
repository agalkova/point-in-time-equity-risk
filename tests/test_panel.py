import unittest

import pandas as pd

from risk_managed_momentum.data.panel import build_point_in_time_panel


class PanelTests(unittest.TestCase):
    def test_dated_alias_maps_provider_series_without_changing_membership_name(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "ticker": ["OLD", "NEW"],
                "close": [10.0, 11.0],
                "volume": [100.0, 110.0],
            }
        )
        membership = pd.DataFrame(
            {"date": ["2024-01-02", "2024-01-03"], "ticker": ["CANON", "CANON"]}
        )
        aliases = [
            {
                "membership_ticker": "CANON",
                "provider_ticker": "OLD",
                "start": "2024-01-01",
                "end": "2024-01-02",
            },
            {
                "membership_ticker": "CANON",
                "provider_ticker": "NEW",
                "start": "2024-01-03",
                "end": "2024-12-31",
            },
        ]
        price, volume, member = build_point_in_time_panel(bars, membership, aliases)
        self.assertEqual(price.loc[pd.Timestamp("2024-01-02"), "CANON"], 10.0)
        self.assertEqual(price.loc[pd.Timestamp("2024-01-03"), "CANON"], 11.0)
        self.assertEqual(volume.loc[pd.Timestamp("2024-01-03"), "CANON"], 110.0)
        self.assertTrue(member.to_numpy().all())


if __name__ == "__main__":
    unittest.main()
