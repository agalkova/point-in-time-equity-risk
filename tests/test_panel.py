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

    def test_index_removal_does_not_truncate_forward_prices(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=4)
        bars = pd.DataFrame(
            {
                "date": dates,
                "ticker": ["OLD"] * 4,
                "close": [10.0, 9.0, 8.0, 7.0],
                "volume": [100.0] * 4,
            }
        )
        membership = pd.DataFrame({"date": dates[:2], "ticker": ["OLD"] * 2})
        price, _, member = build_point_in_time_panel(bars, membership, aliases=[])
        self.assertEqual(price.loc[dates[-1], "OLD"], 7.0)
        self.assertFalse(member.loc[dates[-1], "OLD"])

    def test_asof_alias_does_not_leak_reused_ticker_history(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=3)
        bars = pd.DataFrame(
            {
                "date": dates,
                "ticker": ["REUSE"] * 3,
                "close": [10.0, 100.0, 101.0],
                "volume": [100.0] * 3,
            }
        )
        membership = pd.DataFrame({"date": [dates[0]], "ticker": ["REUSE"]})
        aliases = [
            {
                "membership_ticker": "REUSE",
                "provider_ticker": "REUSE",
                "start": str(dates[0].date()),
                "end": str(dates[0].date()),
                "download_asof": str(dates[0].date()),
            }
        ]
        price, _, _ = build_point_in_time_panel(bars, membership, aliases)
        self.assertEqual(price.loc[dates[0], "REUSE"], 10.0)
        self.assertTrue(price.loc[dates[1] :, "REUSE"].isna().all())


if __name__ == "__main__":
    unittest.main()
