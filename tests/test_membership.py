import unittest

import pandas as pd

from risk_managed_momentum.data.membership import (
    MembershipSource,
    daily_membership,
    symbols_needed_for_period,
)


class MembershipTests(unittest.TestCase):
    def setUp(self) -> None:
        current = pd.DataFrame(
            {
                "ticker": ["NEW", "KEEP"],
                "security": ["New Co", "Keep Co"],
                "cik": [1, 2],
            }
        )
        changes = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-03"]),
                "added_ticker": ["NEW"],
                "added_security": ["New Co"],
                "removed_ticker": ["OLD"],
                "removed_security": ["Old Co"],
                "reason": ["Replacement"],
            }
        )
        self.source = MembershipSource(current=current, changes=changes)

    def test_membership_reverses_changes_before_effective_date(self) -> None:
        result = daily_membership(self.source, start="2024-01-02", end="2024-01-04")
        by_date = result.groupby("date")["ticker"].apply(set)
        self.assertEqual(by_date[pd.Timestamp("2024-01-02")], {"OLD", "KEEP"})
        self.assertEqual(by_date[pd.Timestamp("2024-01-03")], {"NEW", "KEEP"})
        self.assertEqual(by_date[pd.Timestamp("2024-01-04")], {"NEW", "KEEP"})

    def test_symbol_union_includes_removed_names(self) -> None:
        self.assertEqual(
            symbols_needed_for_period(self.source, start="2024-01-01"),
            ["KEEP", "NEW", "OLD"],
        )


if __name__ == "__main__":
    unittest.main()
