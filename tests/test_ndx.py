import unittest

import pandas as pd

from risk_managed_momentum.data.ndx import expand_monthly_membership, month_end_snapshot_dates


class NdxMembershipTests(unittest.TestCase):
    def test_month_end_dates_are_calendar_month_ends(self) -> None:
        result = month_end_snapshot_dates("2024-01-01", "2024-03-31")
        self.assertEqual(
            result.tolist(),
            pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]).tolist(),
        )

    def test_snapshot_is_used_only_after_its_asof_date(self) -> None:
        snapshots = pd.DataFrame(
            {
                "snapshot_date": ["2024-01-31", "2024-01-31", "2024-02-29"],
                "ticker": ["A", "B", "C"],
            }
        )
        result = expand_monthly_membership(
            snapshots,
            start="2024-01-30",
            end="2024-03-01",
        )
        self.assertTrue(result[result["date"].eq(pd.Timestamp("2024-01-30"))].empty)
        self.assertEqual(
            set(result.loc[result["date"].eq(pd.Timestamp("2024-02-15")), "ticker"]),
            {"A", "B"},
        )
        self.assertEqual(
            set(result.loc[result["date"].eq(pd.Timestamp("2024-03-01")), "ticker"]),
            {"C"},
        )


if __name__ == "__main__":
    unittest.main()
